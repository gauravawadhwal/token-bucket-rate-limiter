from flask import Flask, request
import os
import json
from redis import WatchError
from RateLimitTokenService.RateLimitTokenBucket import RateLimitTokenBucket
import time
"""
RateLimitTokenBucketStore
This is the datastore interface for requesting tokens. This implementation is specific to redis 
and transacts the RateLimitTokenBucket objects stored as json records.

The primary transaction method transact_request_token will return the available token to the application, 
and decrement and update the tokens, as well as handling creation etc. 
The other methods are unlikely to be need to be used directly but have been left public incase of future use cases.

Parameter defintions
    instance_key: This uniquely identifies the entity the limit is assigned to, e.g. userId, api key, credit card etc
    bucket_prefix: This will denote a particular kind of limit, as different use cases may have separate pools for the same instance/period etc.
                    e.g. general-endpoint, media-endpoint, expensive-purchases etc
    period: the time period in which they can use max_tokens
    max_tokens: the number of requests that can be made in period
    redis_store: This is the supplied redis connection in form of an initialised redis-py object, 
                    allowing to pass pipelines or separate stores when needed
"""

def transact_request_token(bucket_prefix, max_tokens, period, instance_key, redis_store):
    """This is the callable method, which for given parameters will create/refresh a tokenbucket,
    checks if a token is available, and if it is, removes one. 
    It returns a touple:
        - remaining tokens, (None if the limit is already exhausted and unsucceful, 0 last token by this succesful transaction) 
        - time till next token is generated"""
    # Generate a key for the paramaters which uniquely identify a token bucket
    limit_key = build_limit_key(bucket_prefix, max_tokens, period, instance_key)
    # create a redis 'pipeline' to transact upon
    pipe = redis_store.pipeline(True)

    # Retry loop containing the transaction, as we need to 'watch' the key and retry the transaction if another one occurs in race
    while 1:
        try:
            pipe.watch(limit_key)

            # Grab a token bucket and update it (will make a new one if needed)
            tb = retreive_token_bucket(bucket_prefix, max_tokens, period, instance_key, pipe)
            current_tokens, next_token_seconds = tb.compute_current_tokens()

            # If no tokens available return None
            if current_tokens < 1:
                return None, next_token_seconds
            
            # If avaialable decrement the tokens, and update the datastore
            current_tokens = tb.decrease_tokens(1)

            #set to buffered mode, then attempt to execute
            pipe.multi()
            pipe.set(limit_key, tb.to_json())
            pipe.execute()
            break
        except WatchError:
            continue
        finally:
            pipe.reset()
    
    return current_tokens, next_token_seconds

def create_token_bucket(bucket_prefix, max_tokens, period, instance_key, redis_store):
    """"Creates a new token bucket with the given parameters, serialise and store to redis"""
    limit_key = build_limit_key(bucket_prefix, max_tokens, period, instance_key)
    tb = RateLimitTokenBucket(limit_key, max_tokens, period)
    redis_store.set(limit_key, tb.to_json())
    return tb

def retreive_token_bucket(bucket_prefix, max_tokens, period, instance_key, redis_store):
    """"Gets the token bucket for the given parameters, and if one doesnt exist, create one and returns it"""
    limit_key = build_limit_key(bucket_prefix, max_tokens, period, instance_key)
    current_record = redis_store.get(limit_key)

    if current_record:
        return RateLimitTokenBucket.from_json(current_record)
    else:
        return create_token_bucket(bucket_prefix, max_tokens, period, instance_key, redis_store)

def build_limit_key(bucket_prefix, max_tokens, period, instance_key):
    """Helper method to combine the parameters into a key for use in the datastore to uniquely identify tokenbucket"""
    return "-".join((str(bucket_prefix), str(max_tokens), str(period), str(instance_key)))

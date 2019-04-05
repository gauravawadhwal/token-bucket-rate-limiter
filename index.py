from flask import Flask, request
import os
import redis
from RateLimitTokenService.RateLimitTokenBucketStore import transact_request_token
from functools import wraps
import random
app = Flask(__name__)

redis_store = r = redis.Redis(host='localhost', port=6379, db=0)

"""
---------------Rate Limit Demo Web App-----------------------
This is a simple demo app to walk through how to use the RateLimitTokenBucketStore to enforce rate limits on endpoints
This is a Python Flask web api with some test methods, structured to demonstrate the rate limiter, not structured like a proper app.
You can hit the /, /Pizza and /Pasta Endpoints, with basic auth. It has ratelimits based on username/
"""

# important business entities for our application we'll use later
pizza_toppings = ['mozzarella', 'basil', 'tomato', 'olives', 'chilli']
pasta_varieties = ['gnocchi', 'penne', 'tagliatelle', 'spaghetti', 'cannelloni']
ice_cream_flavours =  ['chocolate', 'cookies n cream', 'hazelnut', 'fudge', 'eggs']

"""
This is a simple example for how an endpoint can use the transact_request_token method
limiting to 7 requests per 30 seconds per username in this case. 
We could do different period/limits, do it by API key instead, or even check multiple limits simultaneously if we wanted here
We're using the general limit prefix, which might be shared with other endpoints
"""

@app.route("/")
def index():
    """simple endpoint that allows 100 requests per hour per user, and returns a 429 when exhausted"""
    # very secure authentication method
    if(not request.authorization):
        return "provide basic auth credentials", 403
    remaining_requests, next_token_seconds = transact_request_token("general", 100, 3600, request.authorization.username, redis_store)
    if remaining_requests is None:
        return f"Rate limit exceeded, try again in {next_token_seconds} seconds", 429
    else:
        return f"You have {remaining_requests} requests remaining"

"""We can make this nicer, lets configure reusable limit pools (specific to this app)
and wrap this so it can be used as a simple decorator (python syntactic sugar)
Normally would break this out separately"""

rate_limit_definitions = {'general': {'max_tokens': 7, 'period': 30}, 'special': {'max_tokens': 1, 'period': 10}}

def rate_limited(rateName):
    def rate_limit_decorator(func):
        @wraps(func)
        def wrap(*args, **kwargs):
            if(not request.authorization):
                return "provide basic auth credentials", 403
            remaining_requests, next_token_seconds = transact_request_token(rateName, 
                                                                            rate_limit_definitions[rateName]['max_tokens'],
                                                                            rate_limit_definitions[rateName]['period'], 
                                                                            request.authorization.username, redis_store)
            if remaining_requests is None:
                return f"Rate Limit Exhausted, try again in {next_token_seconds} seconds", 429
            else:
                return func(*args, **kwargs)
        return wrap
    return rate_limit_decorator


"""The point of this wasnt to show off some cute python syntax, but rather that we can do meaningful things with our endpoints.
 e.g. Pizza and Pasta should share a total request limit, but icecream can have its own limit (that is stricter, its treat!)"""

@app.route("/pizza")
@rate_limited("general")
def pizza():
    return pizza_toppings[random.randrange(len(pizza_toppings))]

@app.route("/pasta")
@rate_limited("general")
def pasta():
    return pasta_varieties[random.randrange(len(pasta_varieties))]

@app.route("/icecream")
@rate_limited("special")
def ice_cream():
    return ice_cream_flavours[random.randrange(len(ice_cream_flavours))]


if __name__ == "__main__":
    app.run()
    redis_store.flushall()
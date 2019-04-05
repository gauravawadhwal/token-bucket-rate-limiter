from RateLimitTokenService.RateLimitTokenBucketStore import transact_request_token
from RateLimitTokenService.RateLimitTokenBucket import RateLimitTokenBucket
from unittest import mock
import time
import fakeredis

"""
Some basic testing around the transaction method for request tokens
"""

redis_store = fakeredis.FakeStrictRedis()

class MockedTime(object):
  def __init__(self):
    self._time = 0.0

  def tick(self, seconds):
    self._time += seconds

  def time(self):
    return self._time

def test_bucket_creation():
        """test a record is created when transacting if there isnt one"""
        redis_store.flushall()
        assert redis_store.get("general-7-30-foo") == None
        transact_request_token("general", 7, 30, 'foo', redis_store)
        assert redis_store.get("general-7-30-foo") != None 

def test_bucket_decrement():
        """test transacting appropriately decrements"""
        redis_store.flushall()
        assert redis_store.get("general-7-30-foo") == None
        transact_request_token("general", 7, 30, 'foo', redis_store)
        tb = RateLimitTokenBucket.from_json(redis_store.get("general-7-30-foo"))
        assert tb.current_tokens == 6 
        transact_request_token("general", 7, 30, 'foo', redis_store)
        tb = RateLimitTokenBucket.from_json(redis_store.get("general-7-30-foo"))
        assert tb.current_tokens == 5

def test_transaction_exhaustion():
        """test using all tokens and then attempting to transact returns none"""
        redis_store.flushall()
        for i in range(0,7):
          transact_request_token("general", 7, 30, 'foo', redis_store)
        assert transact_request_token("general", 7, 30, 'foo', redis_store)[0] == None
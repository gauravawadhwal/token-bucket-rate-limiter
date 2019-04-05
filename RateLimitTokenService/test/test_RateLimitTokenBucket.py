from RateLimitTokenService.RateLimitTokenBucket import RateLimitTokenBucket
from unittest import mock
import time

"""
Not the most exhaustive test suite but handy for ensuring the behaviour is as expected.
Some basic testing around the token bucket operations, and the behaviour of token additions/resets with time
Using a mocked time so the tests are faster.
"""


class MockedTime(object):
  def __init__(self):
    self._time = 0.0

  def tick(self, seconds):
    self._time += seconds

  def time(self):
    return self._time

def test_exhaustion():
        """test quickly decrementing the tokens results in none left"""
        tb = RateLimitTokenBucket('key', 5, 40)
        tb.decrease_tokens(5)
        tb.compute_current_tokens()
        assert tb.current_tokens == 0   

def test_exhaustion_refresh():
        """test decrementing the token and waiting max_count/period seconds adds one token"""
        clock = MockedTime()
        tb = RateLimitTokenBucket('key', 5, 40, clock=clock)
        tb.decrease_tokens(2)
        tb.compute_current_tokens()
        assert tb.current_tokens == 3  
        clock.tick(8)
        tb.compute_current_tokens()
        assert tb.current_tokens == 4 

def test_exhaustion_reset():
        """test waiting period refreshes tokens to exactly the max_count"""
        clock = MockedTime()
        tb = RateLimitTokenBucket('key', 5, 40, clock=clock)
        tb.decrease_tokens(2)
        assert tb.current_tokens == 3  
        clock.tick(100)
        tb.compute_current_tokens()
        assert tb.current_tokens == 5  
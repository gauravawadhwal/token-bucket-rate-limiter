import time
import json

"""
This is a (datstore agnostic) class that stores an instance of a simple token bucket for rate limiting.
After being initialised, the currently available tokens can be computed for the current time via
the method compute_current_tokens.

The decrease_tokens method can also be used decrement tokens when being used.

There are also to_json and from_json methods for convenience of serialisation for storage in a database.

Parameter defintions
    limit_key: a unique id for the token bucket instance. Opaque to this class so implementations of rate limit 
            stores can define their own key structure
    period: the time period in which they can use max_tokens
    max_tokens: the number of requests that can be made in period
"""

class RateLimitTokenBucket:
    def __init__(self, limit_key, max_tokens, period, current_tokens=None, last_update=None, clock=time):
        self.limit_key = limit_key
        self.max_tokens = max_tokens
        self.period = period
        self._clock = clock
        if(current_tokens == None or last_update == None):
            self.reset_tokens()
        else:
            self.current_tokens = current_tokens
            self.last_update = last_update
    
    def reset_tokens(self):
        self.current_tokens = self.max_tokens
        self.last_update = self._clock.time()

    def decrease_tokens(self, decrease_amount):   
         self.current_tokens -= decrease_amount
         return self.current_tokens

    def compute_current_tokens(self):
        seconds_since_update = (self._clock.time() - self.last_update)
        refill_period_seconds = self.period/self.max_tokens
        # Find the number of tokens that should have been added since the last update
        # assuming constant rate
        token_delta = int(seconds_since_update//refill_period_seconds)
        
        # If the token delta is higher than a complete refill, reset the bucket
        if(token_delta + self.current_tokens >= self.max_tokens):
            self.reset_tokens()
        else:
            # otherwise update bucket to the state for the last token top up
            self.current_tokens += token_delta
            self.last_update = self.last_update + token_delta * float(refill_period_seconds)
        # caclulate time till next top up 
        next_token_seconds = refill_period_seconds - (self._clock.time() - self.last_update)
        return self.current_tokens, next_token_seconds

    def to_json(self):
        return json.dumps({'limit_key': self.limit_key,'current_tokens': self.current_tokens, 'max_tokens': self.max_tokens,
                             'period': self.period, 'last_update': self.last_update})

    @staticmethod
    def from_json(json_input):
        redis_dict = json.loads(json_input)
        return RateLimitTokenBucket(redis_dict.get('limit_key'), redis_dict.get('max_tokens'), redis_dict.get('period'),
                                        redis_dict.get('current_tokens'), redis_dict.get('last_update')) 

    


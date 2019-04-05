# token-bucket-rate-limiter
A simple Flask Python app with token bucket rate limiting

## Try it out
Install and start redis locally following [these steps](https://redis.io/topics/quickstart)

To run the application install Python >=3.7.1 

```bash
pip install requirements.txt
```
To run the example app

```bash
python web_app.py
```
To run tests
```bash
pytest RateLimitTokenService/test/
```

You can now send get requests to the following endpoints
 `/` , `/pizza` , `/pasta`

## Design
The example app  implements a rate limit per user limit, with a rolling time window.

The module RateLimitTokenBucket is more generic solution. It's abstracted in a way so we could limit by user, or api-key or any other instance-key with multiple variable time window limits (preferably rolling) for each instance, in parallel, if desired. 

### Algorithm

There are many solutions to this problem, but the style of solution I’ve selected is the ‘token bucket’, inspired by this [blog](https://medium.com/smyte/rate-limiter-df3408325846) and the [wikipedia page](https://en.wikipedia.org/wiki/Token_bucket) on the algorithm.

This methodology is where we maintain a global cache of request tokens per ‘limit key’, which is initialised as a maximum, and then decremented as they are used, and incremented at a constant rate. 

In reality we don’t actually want to increment them all until they are accessed, for efficiency, so we just keep track of the time when the token bucket was last updated, and calculate the current state immediately when we access it.

The limit key idea means that this could be extended to any type of rate limiting, e.g. for credit card fraud detection, you could define a key based on the card and the riskiness of the transaction, and could be set up so you can make 10 transactions a day under 1000$ but only 1 over 1000$ by setting up two limits and defining a limit key using your business logic.

The token bucket method has the advantages of:
- Enforcing a rolling window limit and not falling into the boundary condition of fixed windows
- Simple implementation
- Not requiring much memory per stored limit
- Being scalable and distributable as it can use a database that can be accessed by many nodes, regions etc
- Not requiring any updating or calculation of unused limits

It has a few disadvantages
- Requires extra work to be atomic in its transaction, 
because it requires a read and write - so slight opportunity for race condition where a second request slips through while another one is being checked, when only one should pass, unless this atomicity is added
- Doesn’t keep logs of the times requests were made, so cant use a single record for multiple rate limits
- Need to be careful with timestamp resolution for adding additional tokens

## Implementation
I decided to use python for this simple demonstration, with a flask webserver. It wouldn’t be my ideal choice for a more complex web app at a large scale, but it does fine for small apps, and is very readable and good for demonstrating architectures like this problem. In a production app I’d generally use Java or something similar, but I probably also would be using a library rather than spinning my own rate limiter!

I decided to use redis as the store. This uses a pattern that would allow distributed rate limiting, because it can be used as a global cache. In production you could also use something more advanced like rocksDB or thrift, and have disk backing, as well as region replication etc, but this same principle and pattern would apply for using a single global cache which stateless web servers request a rate limit from via transactions. 

### File by file

#### index.py 
This is the stateless flask app with a few endpoints that have a few rate limits. It uses basic auth to get a username which it builds rate limits for

#### RateLimitTokenBucket.py
This is a (datstore agnostic) class that stores an instance of a simple token bucket for rate limiting.
After being initialised, the currently available tokens can be computed for the current time via
the method compute_current_tokens.
The decrease_tokens method can also be used decrement tokens when being used.
There are also to_json and from_json methods for convenience of serialisation for storage in a database.

#### RateLimitTokenBucketStore.py
This is the datastore interface for requesting tokens to be used by the application. This implementation is specific to redis and transacts the RateLimitTokenBucket objects stored as json records.

The primary transaction method transact_request_token will return the available token to the application, and decrement and update the tokens, as well as handling creation etc. 
The other methods are unlikely to be need to be used directly but have been left public incase of future use cases.




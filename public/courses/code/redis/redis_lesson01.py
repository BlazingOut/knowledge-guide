import redis

client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    db=0,
    decode_responses=True,
)

value = client.get("greeting")
login_info = client.get("login:session:abc123")
print(value)
print(login_info)
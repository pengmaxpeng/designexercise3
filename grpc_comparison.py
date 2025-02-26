import time
import chat_pb2

def grpc_encode(data):
    # Create a SendMessageRequest protobuf message from the test data.
    msg = chat_pb2.SendMessageRequest(
        sender=data.get("from", ""),
        recipient=data.get("to", ""),
        content=data.get("body", "")
    )
    return msg.SerializeToString()

def grpc_decode(data_bytes):
    msg = chat_pb2.SendMessageRequest()
    msg.ParseFromString(data_bytes)
    return msg

def measure_encoding(data, encode_func, iterations=10000):
    total_size = 0
    start = time.time()
    encoded = None
    for _ in range(iterations):
        encoded = encode_func(data)
        total_size += len(encoded)
    duration = time.time() - start
    avg_size = total_size / iterations
    return avg_size, duration, encoded

def measure_decoding(encoded, decode_func, iterations=10000):
    start = time.time()
    for _ in range(iterations):
        _ = decode_func(encoded)
    duration = time.time() - start
    return duration

def main():
    iterations = 100000
    test_data = {
        "cmd": 3,  # Not used by the protobuf message
        "from": "Alice",
        "to": "Bob",
        "body": "Hello Bob, let's measure gRPC (protobuf) efficiency!"
    }
    
    avg_size_grpc, enc_time_grpc, encoded_grpc = measure_encoding(test_data, grpc_encode, iterations)
    dec_time_grpc = measure_decoding(encoded_grpc, grpc_decode, iterations)
    
    print("gRPC (Protobuf) Implementation:")
    print(f"Average size: {avg_size_grpc:.2f} bytes")
    print(f"Encoding {iterations} times: {enc_time_grpc:.6f} seconds")
    print(f"Decoding {iterations} times: {dec_time_grpc:.6f} seconds")

if __name__ == "__main__":
    main()

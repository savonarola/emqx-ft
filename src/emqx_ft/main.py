import argparse
import hashlib
import json
import logging

import paho.mqtt.client as mqtt


def main():
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser("emqx-ft")
    parser.add_argument("--port", default=1883, type=int)
    parser.add_argument("--host", default="127.0.0.1", type=str)
    parser.add_argument("--file", required=True, type=argparse.FileType("r"))
    parser.add_argument("--segment-size", default=1024, type=int)
    parser.add_argument("--file-id", required=True, type=str)
    parser.add_argument("--client-id", required=True, type=str)
    args = parser.parse_args()

    data = open(args.file.name, "rb").read()

    hash = hashlib.new('sha256')
    hash.update(data)
    checksum = hash.hexdigest()

    meta = {
        "name": args.file.name,
        "size": len(data)
    }

    topic_prefix = f"$file/{args.file_id}"

    client = mqtt.Client(client_id=args.client_id)
    client.protocol_version = mqtt.MQTTv5
    client.enable_logger(logging.getLogger())
    client.connect(args.host, args.port, 60)
    client.publish(f"{topic_prefix}/init", json.dumps(meta), qos=1)
    for offset, chunk in segments(data, args.segment_size):
        client.publish(f"{topic_prefix}/{offset}", chunk, qos=1)
    info = client.publish(f"{topic_prefix}/fin", "", qos=1)

    def on_publish(client, userdata, mid):
        if mid == info.mid:
            client.disconnect()

    client.on_publish = on_publish

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()
        print("Disconnected")


def segments(data, segment_size):
    offset = 0
    while offset < len(data):
        yield (offset, data[offset:offset + segment_size])
        offset += segment_size


if __name__ == "__main__":
    main()


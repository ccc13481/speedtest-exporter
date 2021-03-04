import subprocess
import json
import datetime
import os
from prometheus_client import make_wsgi_app, Gauge
from flask import Flask

app = Flask("Speedtest-Exporter") #Create flask app

# Create Metrics
server = Gauge('speedtest_server_id', 'Speedtest server ID used to test')
jitter = Gauge('speedtest_jitter_latency_milliseconds', 'Speedtest current Jitter in ms')
ping = Gauge('speedtest_ping_latency_milliseconds', 'Speedtest current Ping in ms')
download_speed = Gauge('speedtest_download_bits_per_second', 'Speedtest current Download Speed in bit/s')
upload_speed = Gauge('speedtest_upload_bits_per_second', 'Speedtest current Upload speed in bits/s')

def bytes_to_bits(bytes_per_sec):
    return bytes_per_sec * 8

def bits_to_megabits(bits_per_sec):
    megabits = round(bits_per_sec * (10**-6),2)
    return str(megabits) + " Mb/s"

def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True

def runTest():
    serverID = os.environ.get('SPEEDTEST_SERVER')
    cmd = ["speedtest", "--format=json-pretty", "--progress=no", "--accept-license", "--accept-gdpr"]
    if serverID:
        cmd.append(f"--server-id={serverID}")
    output = subprocess.check_output(cmd)
    if is_json(output):
            data = json.loads(output)
            if "error" in data:
                # If we get here it probably means that socket timed out(Network issues?)
                print('Something went wrong')
                print(data['error'])
                return None
            if "type" in data:
                if data['type'] == 'log':
                    print(str(data["timestamp"]) + " - " + str(data["message"]))
                if data['type'] == 'result':
                    actual_server = int(data['server']['id'])
                    actual_jitter = data['ping']['jitter']
                    actual_ping = data['ping']['latency']
                    download = bytes_to_bits(data['download']['bandwidth'])
                    upload = bytes_to_bits(data['upload']['bandwidth'])
                    return (actual_server, actual_jitter, actual_ping, download, upload)

@app.route("/metrics")
def updateResults():
    r_server, r_jitter, r_ping, r_download, r_upload = runTest()
    server.set(r_server)
    jitter.set(r_jitter)
    ping.set(r_ping)
    download_speed.set(r_download)
    upload_speed.set(r_upload)
    current_dt = datetime.datetime.now()
    print(current_dt.strftime("%d/%m/%Y %H:%M:%S - ") + "Server: " + str(r_server) + " | Jitter: " + str(r_jitter) + " ms | Ping: " + str(r_ping) + " ms | Download: " + bits_to_megabits(r_download) + " | Upload:" + bits_to_megabits(r_upload))
    return make_wsgi_app()

@app.route("/")
def mainPage():
    return "<h1>Welcome to Speedtest-Exporter.</h1>Click <a href='/metrics'>here</a> to see metrics."


if __name__ == '__main__':
    PORT = os.getenv('SPEEDTEST_PORT', 9798)
    app.run(host='0.0.0.0', port=PORT) # Start flask app

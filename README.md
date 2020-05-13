# Python Tcp Client

Simple tcp client implement in python3

# Dependencies

- glog: For logging.  ```pip install glog```

# Usage

```shell
usage: TcpClient.py [-h] [-s SIZE] [-t TIMEOUT] [-e ENCODING] Address Port

positional arguments:
  Address               Adress or hostname of tcp server
  Port                  Port of tcp server

optional arguments:
  -h, --help            show this help message and exit
  -s SIZE, --size SIZE  Receive buffer size
  -t TIMEOUT, --timeout TIMEOUT
                        Timeout of tcp connection and receive
  -e ENCODING, --encoding ENCODING
                        Encoding that will used in tcp communication
```


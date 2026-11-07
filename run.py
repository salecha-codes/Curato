"""Start Curato AI: the Python models, API and website share one address."""
import argparse
from backend.app import create_app

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--strictPort',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    create_app().run(host=args.host,port=args.port,debug=False)

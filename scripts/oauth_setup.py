"""Owner-local OAuth entrypoint. Never used by a render workflow or artifact."""
import argparse,json
from pathlib import Path
from channel.oauth import authorize,oauth_status

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Secure owner-local YouTube Desktop consent; no upload')
    p.add_argument('--client-secrets',type=Path,default=Path('.secrets/client_secrets.json'))
    p.add_argument('--token-file',type=Path,default=Path('.secrets/youtube-token.json'))
    p.add_argument('--status',action='store_true')
    a=p.parse_args()
    result=oauth_status(a.token_file) if a.status else authorize(a.client_secrets,a.token_file)
    print(json.dumps(result,indent=2))

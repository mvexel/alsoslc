# alsoslc
Site generator for https://alsoslc.com

## Initial Setup

```
$ python3 -m venv venv
$ source venv/bin/activate
(venv) $ pip install -r requirements.txt
```

## Environment Variables

```
ALSOSLC_SOURCE=/path/to/images/
ALSOSLC_SITE=/path/to/local/site
ALSOSLC_REMOTE=user@host:/path/to/site
```

## Deploy

```
./deploy.sh
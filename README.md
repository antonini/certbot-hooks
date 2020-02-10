# Certbot Hooks

## Introdution

This project was created to store hooks scripts that is going to be used on the certificate generation process of [certbot](https://github.com/certbot/certbot) (Let's Encrypt).

Below are a list of files, it purpose and usage instructions.


### cloudflare-deploy.py

#### Overview

That hook was created due the given situation: You use Cloudflare as your DNS server and also your WAF.

So you need to use Cloudflare to authenticate the certbot using a DNS record (See the certbot-dns-cloudflare plugin for certbot that is responsible for that) and also have to deploy your private key and certificate to Cloudflare.

That hook was created to do that action. To deploy the private key and certificate to Cloudflare.

#### Installing

Clone the repository to a folder on the machine that you are going to use to generate the certificate. I'll assume that you cloned on the `/opt` directory, so the main folder will be `/opt/certbot-hooks/`.

The command bellow will create a pair of keys locally and sign that using certbot and the hook will deploy that on Cloudflare.

```
sudo certbot certonly \
  --dns-cloudflare \
  --deploy-hook /opt/certbot-hooks/cloudflare-deploy.py \
  --dns-cloudflare-credentials ~/.secrets/certbot/cloudflare.ini \
  --dns-cloudflare-propagation-seconds 5 \
  -d example.com
```

## Contributions

If you want to contribute create an issue and if you know what you are doing create a PR.
The bot is a client for Deluge torrent server.

## Prerequisites
- create bot user via [BotFather and get API token](https://core.telegram.org/bots#3-how-do-i-create-a-bot);
- you have to setup Deluge server on your own (this bot doesn't cover the setup of the server part);
- Docker.

## Run the bot in Docker container
### Environment variables
Before you run the container, you need to prepare several environment variables:

| Variable           | Description                                                                         | Default               |
| ------------------ | ----------------------------------------------------------------------------------- | --------------------- |
| TELEGRAM_BOT_TOKEN | API token that BotFather gives you when you create a bot                            | none                  |
| DELUGE_HOST        | IP address of a server with Deluge                                                  | none                  |
| DELUGE_PORT        | Port of Deluge daemon server                                                        | 58846                 |
| DELUGE_USERNAME    | Deluge user                                                                         | localclient           |
| DELUGE_PASSWORD    | Password of Deluge user                                                             | none          |
| ADMINS             | Comma-separated list of telegram IDs that should have access to all Deluge torrents | 294967926             |
| AUTHORIZED_USERS   | Comma-separated IDs of Telegram users that are allowed to interact with the bot     | '294967926,191151492' |

### Build Docker image
```sh
$ docker build -t deluge_mgmt_bot_image .
```

### Start the container

![Docker Image Version (latest semver)](https://img.shields.io/docker/v/:liamnou/:deluge_mgmt_bot)

```sh
$ docker run -dit \
    --env TELEGRAM_BOT_TOKEN=... \
    --env DELUGE_HOST=... \
    --env DELUGE_PASSWORD=... \
    --restart unless-stopped \
    --name=deluge_mgmt_bot deluge_mgmt_bot_image
```

# VGRAM Telegram Shop Bot

Telegram shop bot deployed as a Render Background Worker. The bot uses SQLite; the Render blueprint mounts persistent storage at `/var/data`.

## Deploy on Render

1. In Render, choose **New → Blueprint** and connect `ramzilzokirov-lgtm/VGRAM`.
2. Render reads `/render.yaml`. It creates the `vgram-shop-bot` worker and persistent disk.
3. Set the secret environment variable `BOT_TOKEN` to the bot token from BotFather. Do not commit tokens to GitHub.
4. Deploy the worker and check the logs for `VGRAM shop bot starting`.

The Telegram admin ID is configured as `ADMIN_ID=8436409687` in the blueprint.

## Shop categories

- `numbers` — +888 numbers
- `stars` — Telegram Stars
- `premium` — Telegram Premium
- `nfts` — NFTs

Products and prices are manually entered by the admin. A customer order creates a request for the admin; automatic payments are not enabled.

## Bot commands

- `/start` — open shop
- `/help` — help
- `/health` — check bot
- `/admin` — admin panel (admin ID only)
- `/addproduct category | name | price | stock` — add product
- `/setprice ID | price` — update price
- `/setstock ID quantity` — update stock
- `/ban Telegram_ID` and `/unban Telegram_ID` — restrict/restore access
- `/broadcast message` — prepare a broadcast and confirm it in Telegram

Use prices as readable text, e.g. `5 EUR` or `250 UAH`. Verify that you are allowed to sell any digital goods and that each listing is genuine before adding it.


## VGRAM Stars wallet
- Each newly registered VGRAM account receives **1,000 internal VGRAM Stars** exactly once.
- These are project-internal credits, not Telegram Stars and not credits issued by Google Play.
- The server records the registration bonus in `star_ledger` with a unique event key and exposes the balance through `GET /account/wallet`.
- Login does not award additional Stars.
- NFT prices are not hardcoded as universal values: official Telegram gift prices and collectible resale prices vary by gift/market listing. To mirror them accurately, the catalogue must be populated from current official Telegram gift data / marketplace listings rather than guessed fixed prices.

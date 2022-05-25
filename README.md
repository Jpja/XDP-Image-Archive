# Dogeparty Image Archive

Downloads all images from Dogeparty and saves them to an archive.

View archive: https://
Youtube explainer:  https://

## Problems It Solves

Most Dogeparty NFTs provide a URL link to an associated image file. Although these URLs are perfectly preserved by the blockchain, the images they point to are not. This leads to several issues:

1) If a link dies, the NFT image is "gone".

2) If the target file is changed, the NFT is silently changed as well.

3) If a main image host (e.g. Imgur) ceases operations, the ecosystem as a whole is at risk. 

## How It Works

The script `archiver.py` finds all asset issuances from the Dogeparty DB.

For each issuance, look for an image or json URL from the asset description.

If json URL, open it and look for image URL.

For each asset with an image URL, download image, make a downsized copy and generate sha256 of both.

Build a html directory of all images with checksums.

Write a receipt file of all issuances, URLs and checksums.

Broadcast the hash of the receipt to the blockchain. 

## Why This Solves The Problems 

The archive contains a copy of all images (insofar the URLs are still working). This creates a snapshot of Dogeparty.

The receipt, as long as a copy of it is preserved, is an immutable proof of the snapshot once its checksum is broadcast onchain.

Since the receipt contains sha256 values of all downloaded images, the underlying images also become immutable.

## Considerations

### Libraries

Pillow must be installed; try `pip install pillow`

### Counterparty

This script works for Counterparty too. Simply point it to a Counterparty DB.

### Dishonest Nodes

If an archive is created by a dishonest actor, an image may be replaced with a fake one. To minimize this risk, several node operators should run this script. The more archives that are generated, the stronger the consensus. This is how blockchain consensus works in general.

### Old URLs

The current image is saved. This script can not determine if a URL initially provided the same file as the one downloaded today.

### Proof in Json ≠ Immutable

In some cases the URL contains the file checksum. However, if this URL is extracted from a json file, this is itself not an immutable proof. Use the Timeline Tool to inspect to inspect an asset for onchain data.

* https://github.com/Jpja/XCP-Asset-Timeline 

### Imgur

Imgur doesn't allow editing of images. Therefore you can be quite confident that the Imgur image you see is the original. However, the identifier they use is not a hash, so Imgur is good only as far as you can trust them. This archive minimizes the need for trusting centralized services such as Imgur.  

### NFT Creators

It is recommended that you keep your own Dogeparty node and run this script after you've minted your NFTs. Not only is it good for the ecosystem, but you provide an "official" proof of your own NFTs since the broadcast then is signed by your address. This eliminates the theoretical issue of a "dishonest node" replacing your images with fakes.

### Token Collectors

Save a local copy of the receipt file.

Then navigate the archive and save the original and downsized versions of the relavant images.

Keep these files safe and unmodified. By keeping backups your NFT is safe from linkrot.

### Service Providers

Run this script with the image size set to whatever best suits your service.

In my case the full set of original images made up 4.55 GB, while the copies downsized to max 500px used 366 MB – a saving of 92%.

## Donate

* BTC: bc1qg8vldv8kk4mqafs87z2yv0xpq4wr4csucr3cj7
* DOGE: DChdsuLuEvAPZb9ZXpiEpimgidSJ5VqShq
* ETH: 0x4144CbaF54044510AB2F2f3c51061Dd5558cD604

## License

MIT
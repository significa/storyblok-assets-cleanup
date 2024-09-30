# Cleanup Storyblok assets


[![PyPI version storyblok-assets-cleanup](https://img.shields.io/pypi/v/storyblok-assets-cleanup.svg)](https://pypi.python.org/pypi/storyblok-assets-cleanup/)
[![CI/CD](https://github.com/significa/storyblok-assets-cleanup/actions/workflows/ci-cd.yaml/badge.svg)](https://github.com/significa/storyblok-assets-cleanup/actions/workflows/ci-cd.yaml)

storyblok-assets-cleanup is an utility to find and delete unused assets
(images, videos, documents, etc) in the Storyblok CMS.

Features:

- Find assets without references;
- Output a summary of file to be deleted, grouped by folder;
- Perform a backup of assets before deletion;


## Getting started

### Requirements

- Have a Storyblok space and create a
  [personal access token](https://app.storyblok.com/#/me/account?tab=token)

### Installation

`pip3 install storyblok-assets-cleanup`

## Usage

<!--
  To update the code block with the usage below:
  
  1. Resize your terminal to 100 columns. On most systems just run: `stty cols 100 rows 50`.
  2. Run `storyblok-assets-cleanup --help` to get the usage output.
-->

```
usage: storyblok-assets-cleanup [-h] [--token TOKEN] --space-id SPACE_ID
                                [--region {eu,us,ca,au,cn}] [--delete | --no-delete]
                                [--backup | --no-backup] [--backup-directory BACKUP_DIRECTORY]
                                [--cache | --no-cache] [--cache-directory CACHE_DIRECTORY]
                                [--continue-download-on-failure | --no-continue-download-on-failure]
                                [--blacklisted-folder-paths BLACKLISTED_FOLDER_PATHS]
                                [--blacklisted-words BLACKLISTED_WORDS]

storyblok-assets-cleanup an utility to delete unused assets.

options:
  -h, --help            show this help message and exit
  --token TOKEN         Storyblok personal access token, alternatively use the env var
                        STORYBLOK_PERSONAL_ACCESS_TOKEN.
  --space-id SPACE_ID   Storyblok space ID, alternatively use the env var STORYBLOK_SPACE_ID.
  --region {eu,us,ca,au,cn}
                        Storyblok region (default: EU)
  --delete, --no-delete
                        If we should delete assets, default to false.
  --backup, --no-backup
                        If we should backup assets (to the directory specified in `--backup-
                        directory`), defaults to true.
  --backup-directory BACKUP_DIRECTORY
                        Backup directory, defaults to ./assets_backup.
  --cache, --no-cache   If we should use cache the assets index. Defaults to True (recommended).
  --cache-directory CACHE_DIRECTORY
                        Cache directory, defaults to ./cache.
  --continue-download-on-failure, --no-continue-download-on-failure
                        If we should continue if the download of an asset fails. Defaults to true.
  --blacklisted-folder-paths BLACKLISTED_FOLDER_PATHS
                        Comma separated list of filepaths that should be ignored. Alternatively
                        use the env var BLACKLISTED_ASSET_FOLDER_PATHS. Default to none/empty
                        list.
  --blacklisted-words BLACKLISTED_WORDS
                        Comma separated list of words that should be used to ignore assets when
                        they are contained in its filename. Alternatively use the env var
                        BLACKLISTED_ASSET_FILENAME_WORDS. Default to none/empty list.
```

## Development

- Ensure you have `make` installed.
- Create a virtual environment: `make setup-venv`.
- Install dependencies: `make install-deps`.

Then you can install (link) the repo globally with `make local-install`.

Before pushing changes ensure your code is properly formatted with `make lint`.
Auto format the code with `make format`.

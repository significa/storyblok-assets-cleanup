[![significa's banner](https://raw.githubusercontent.com/significa/.github/refs/heads/main/assets/significa-github-banner-small.png)](https://significa.co/)

# Cleanup Storyblok assets

[![PyPI version storyblok-assets-cleanup](https://img.shields.io/pypi/v/storyblok-assets-cleanup.svg)](https://pypi.python.org/pypi/storyblok-assets-cleanup/)
[![CI/CD](https://github.com/significa/storyblok-assets-cleanup/actions/workflows/ci-cd.yaml/badge.svg)](https://github.com/significa/storyblok-assets-cleanup/actions/workflows/ci-cd.yaml)

**storyblok-assets-cleanup** is a CLI utility to find and delete unused assets
(images, videos, documents, etc) in the Storyblok CMS.

Features:

- Find assets without references;
- Output a summary of assets to be deleted, grouped by folder;
- Perform a backup of assets before deletion;
- Delete the actual assets.


## Getting started

### Requirements

- Have a Storyblok space and create a
[personal access token](https://app.storyblok.com/#/me/account?tab=token)

### Installation

In order to keep your system tidy and without conflicts in your global and user packages,
we recommend [pipx](https://github.com/pypa/pipx):

```
pipx install storyblok-assets-cleanup
```

This should do the trick for all systems.
Adapt the installation command to fit your and preferred tool.

Use `pipx upgrade storyblok-assets-cleanup` to update to the latest release.
Check the package releases on [PyPI](https://pypi.org/project/storyblok-assets-cleanup/).

## Usage

<!--
  To update the code block with the usage below:
  
  1. Resize your terminal to 100 columns. On most systems just run: `stty cols 100 rows 50`.
  2. Run `storyblok-assets-cleanup --help` to get the usage output.
-->

```
usage: storyblok-assets-cleanup [-h] --token TOKEN --space-id SPACE_ID [--region {eu,us,ca,au,cn}]
                                [--delete | --no-delete] [--backup | --no-backup]
                                [--backup-directory BACKUP_DIRECTORY] [--cache | --no-cache]
                                [--cache-directory CACHE_DIRECTORY]
                                [--continue-download-on-failure | --no-continue-download-on-failure]
                                [--ignore-path IGNORE_PATH] [--ignore-word IGNORE_WORD]

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
  --ignore-path IGNORE_PATH
                        Absolute filepaths that should be ignored, can be passed multiple times.
                        Does not support prefixes, meaning you would need to pass the full path
                        for each directory, as seen in the summary table (with starting slash and
                        without trailing slash). Optional, defaults to no blacklisted paths.
                        Example: --ignore-path '/Do not delete/emails' --ignore-path '/Do not
                        delete/logos'.
  --ignore-word IGNORE_WORD
                        Will not delete assets which contains the specified words in its filename.
                        Default to none/empty list.
```

## Development

- Ensure you have `make` installed.
- Create a virtual environment: `make setup-venv`.
- Install dependencies: `make install-deps`.

Then you can install (link) the local repository globally with `make local-install`.

Before pushing changes ensure your code is properly formatted with `make lint`.
Auto format the code with `make format`.

## License 

MIT

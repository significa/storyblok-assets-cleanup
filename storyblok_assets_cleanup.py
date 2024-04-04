#!/usr/bin/env python3

import argparse
import json
import pathlib
import shutil
from os import getenv, makedirs, path

import requests

_storyblok_space_id = None
_storyblok_personal_access_token = None


def init_storyblok_client(space_id, token):
    # TODO: make this cleaner without changing too much code
    global _storyblok_space_id
    global _storyblok_personal_access_token

    _storyblok_space_id = space_id
    _storyblok_personal_access_token = token


def request(method, path, params=None, **kwargs):
    BASE_URL = 'https://mapi.storyblok.com'

    return requests.request(
        method,
        f'{BASE_URL}/v1/spaces/{_storyblok_space_id}{path}',
        headers={
            'Authorization': _storyblok_personal_access_token,
        },
        params=params,
        **kwargs,
    )


def ensure_cache_dir_exists(cache_directory):
    if not path.exists(cache_directory):
        makedirs(cache_directory)


def load_json(file_path):
    print(f'Loading {file_path}')
    with open(file_path, 'r') as file:
        return json.load(file)


def save_json(file_path, data):
    try:
        with open(file_path, 'w') as file:
            return json.dump(data, file, indent=2, ensure_ascii=True)
    except KeyboardInterrupt as e:
        print("KeyboardInterrupt: Saving file again!")
        save_json(file_path, data)
        raise e


def download_asset(asset_url, target_file_path, continue_download_on_failure):
    print(f'Downloading asset {asset_url!r} into {target_file_path!r}')

    response = request('GET', asset_url, stream=True)

    if not response.ok:
        msg = f'Cannot download asset {asset_url}, got status code {response.status_code}'

        if continue_download_on_failure:
            print(msg)
            return

        raise RuntimeError(
            f'{msg}. --continue-download-on-failure to ignore',
        )

    with open(target_file_path, 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)


def get_all_paginated(path, item_name, params={}):
    page = 1

    all_items = []

    while page is not None:
        print(f'Getting {path}, page={page}')

        params = {
            'per_page': 100,
            **params,
            'page': page,
        }

        response = request(
            'GET',
            path,
            params=params
        )

        response.raise_for_status()
        response_data = response.json()

        if item_name not in response_data and isinstance(response_data, dict):
            raise KeyError(
                'item_name {!r} not in response. Possible keys {}'.format(
                    item_name,
                    ", ".join(response_data.keys())
                )
            )

        new_items = response_data[item_name]

        page = None if len(new_items) < int(params['per_page']) else page + 1

        all_items.extend(new_items)

    return all_items


def is_asset_in_use(asset):
    file_path = asset['filename'].replace('https://s3.amazonaws.com/a.storyblok.com', '')

    response = request(
        'GET',
        '/stories',
        params={
            'reference_search': file_path,
            'per_page': 1,
            'page': 1,
        }
    )

    response.raise_for_status()

    stories = response.json()['stories']

    return len(stories) != 0


def _main():
    parser = argparse.ArgumentParser(
        description='storyblok-assets-cleanup an utility to delete unused assets.'
    )

    parser.add_argument(
        '--delete',
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help='If we should delete assets, default to false.',
    )
    parser.add_argument(
        '--backup',
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help='If we should backup assets (to ./assets_backup/<SPACE_ID>), defaults to true.',
    )
    parser.add_argument(
        '--cache',
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help=(
            'If we should use cache the assets index. Defaults to True (recommended).'
        ),
    )
    parser.add_argument(
        '--continue-download-on-failure',
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help='If we should continue if the download of an asset fails. Defaults to true.',
    )

    parser.add_argument(
        '--space-id',
        type=str,
        default=getenv('STORYBLOK_SPACE_ID'),
        required=getenv('STORYBLOK_SPACE_ID') is None,
        help=(
            'Storyblok space ID, alternatively use the env var STORYBLOK_SPACE_ID.'
        ),
    )
    parser.add_argument(
        '--token',
        type=str,
        default=getenv('STORYBLOK_PERSONAL_ACCESS_TOKEN'),
        required=getenv('STORYBLOK_PERSONAL_ACCESS_TOKEN') is None,
        help=(
            'Storyblok personal access token, '
            'alternatively use the env var STORYBLOK_PERSONAL_ACCESS_TOKEN.'
        ),
    )
    parser.add_argument(
        '--blacklisted-folder-paths',
        type=str,
        default=getenv('BLACKLISTED_ASSET_FOLDER_PATHS', ''),
        help=(
            'Comma separated list of filepaths that should be ignored. '
            'Alternatively use the env var BLACKLISTED_ASSET_FOLDER_PATHS. '
            'Default to none/empty list.'
        ),
    )
    parser.add_argument(
        '--blacklisted-words',
        type=str,
        default=getenv('BLACKLISTED_ASSET_FILENAME_WORDS', ''),
        help=(
            'Comma separated list of words that should be used to ignore assets when they are '
            'contained in its filename. '
            'Alternatively use the env var BLACKLISTED_ASSET_FILENAME_WORDS. '
            'Default to none/empty list.'
        ),
    )
    parser.add_argument(
        '--cache-directory',
        type=str,
        default='cache',
        help='Cache directory, defaults to ./cache.',
    )
    parser.add_argument(
        '--backup-directory',
        type=str,
        default='assets_backup',
        help='Backup directory, defaults to ./assets_backup.',
    )

    args = parser.parse_args()

    init_storyblok_client(args.space_id, args.token)
    should_delete_images = args.delete
    use_cache = args.cache
    backup_assets = args.backup
    space_id = args.space_id
    continue_download_on_failure = args.continue_download_on_failure
    blacklisted_asset_folder_paths = args.blacklisted_folder_paths.split(',')
    blacklisted_asset_filename_words = args.blacklisted_words.split(',')
    cache_directory = args.cache_directory
    backup_directory = args.backup_directory
    assets_cache_path = path.join(cache_directory, f'{space_id}_assets.json')
    asset_folder_cache_path = path.join(cache_directory, f'{space_id}_asset_folders.json')

    ensure_cache_dir_exists(cache_directory)

    all_assets = None
    all_folders = None

    if path.exists(assets_cache_path) and use_cache:
        all_assets = load_json(assets_cache_path)
    else:
        all_assets = get_all_paginated('/assets', item_name='assets')
        save_json(assets_cache_path, all_assets)

    if path.exists(asset_folder_cache_path) and use_cache:
        all_folders = load_json(asset_folder_cache_path)
    else:
        all_folders = get_all_paginated('/asset_folders', item_name='asset_folders')
        save_json(asset_folder_cache_path, all_folders)

    folder_ids_to_folder = {
        folder['id']: folder
        for folder in all_folders
    }

    def get_folder_path_name(folder_id):
        folder = folder_ids_to_folder[folder_id]
        name = folder['name']

        if folder['parent_id'] in [None, '', 0, '0']:
            return f'/{name}'

        if folder['parent_id'] not in folder_ids_to_folder:
            raise RuntimeError(f'Parent asset folder of {folder["id"]} does not exist!')

        parent_path = get_folder_path_name(folder['parent_id'])

        return f'{parent_path}/{name}'

    def should_be_deleted(asset_path_name, filename):
        if asset_path_name in blacklisted_asset_folder_paths:
            print(f'Skipping {id} as it is in {asset_path_name}')
            return False

        if any(word in filename for word in blacklisted_asset_filename_words):
            print(f'Skipping {id} as it contains blacklisted words')
            return False

        return True

    print('Checking for assets in use. This might take a while.')

    count = 0
    for asset in all_assets:
        if 'is_in_use' in asset:
            continue

        asset['is_in_use'] = is_asset_in_use(asset)
        asset['to_be_deleted'] = False

        count += 1

        if count % 25 == 0:
            print(f'{count}/{len(all_assets)}')
            save_json(assets_cache_path, all_assets)

    assets_not_in_use = [
        asset
        for asset in all_assets
        if not asset['is_in_use'] and not asset.get('is_deleted', False)
    ]

    folder_id_to_path_name = {
        folder['id']: get_folder_path_name(folder['id'])
        for folder in all_folders
    }

    folder_id_to_path_name[None] = '/'

    folder_path_names_to_item_counts = {}

    for asset in assets_not_in_use:
        id = asset["id"]

        asset_path_name = folder_id_to_path_name[asset['asset_folder_id']]

        to_be_deleted = should_be_deleted(asset_path_name, asset["filename"])
        asset['to_be_deleted'] = to_be_deleted

        not_in_use_count, to_be_deleted_count = folder_path_names_to_item_counts.setdefault(
            asset_path_name,
            (0, 0)
        )

        folder_path_names_to_item_counts[asset_path_name] = (
            not_in_use_count + 1,
            to_be_deleted_count + 1 if to_be_deleted else to_be_deleted_count
        )

    print('\nSummary of files to be deleted')
    TITLES = [
        'Not in use',
        'To be deleted',
        'Path',
    ]

    def print_padded(outputs):
        print(
            " | ".join([
                (
                    str(output).rjust(len(TITLES[index]), " ")
                    if isinstance(output, int) else
                    str(output).ljust(len(TITLES[index]), " ")
                )
                for index, output in enumerate(outputs)
            ])
        )

    print_padded(TITLES)

    for path_name in sorted(folder_path_names_to_item_counts.keys()):
        not_in_use_count, to_be_deleted_count = folder_path_names_to_item_counts[path_name]

        print_padded([
            not_in_use_count,
            to_be_deleted_count,
            path_name,
        ])

    print()

    if should_delete_images:
        should_delete_images = input('Do you really want to delete the assets? (y/n): ') == 'y'
    elif backup_assets:
        input('Images will not be deleted but will perform backup. Press any key to continue: ')
    else:
        input('Dry run mode: nothing will be done. Press any key to continue: ')

    for asset in assets_not_in_use:
        id = asset["id"]

        asset_path_name = folder_id_to_path_name[asset['asset_folder_id']]

        extension = pathlib.Path(asset["filename"]).suffix

        if backup_assets and asset.get('backed_up_to') is not None:
            file_path = path.join(
                backup_directory,
                space_id,
                f'{id}{extension}',
            )

            download_asset(
                asset["filename"],
                file_path,
                continue_download_on_failure,
            )

            asset['backed_up_to'] = file_path

        if should_delete_images:
            print(f'Deleting asset {id}')

            response = request(
                'DELETE',
                f'/assets/{id}',
            )
            response.raise_for_status()

            asset['is_deleted'] = True

        else:
            print(f'Would delete asset {id!r} if delete mode was on (--delete)')

        if backup_assets or should_delete_images:
            save_json(assets_cache_path, all_assets)


def main():
    try:
        _main()
    except KeyboardInterrupt:
        print('\nInterrupted, exiting...')


if __name__ == '__main__':
    main()

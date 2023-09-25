import requests
from csv import DictReader, writer, reader
import shutil
from os import path, getenv
import pathlib
import json


def get_env(name):
    value = getenv(name)
    if not value:
        raise RuntimeError(f'Env var {name} missing')
    return value


BASE_URL = 'https://mapi.storyblok.com'
HEADERS = {'Authorization': get_env('STORYBLOK_MANAGEMENT_TOKEN')}
SPACE_ID = get_env('STORYBLOK_SPACE_ID')

ASSETS_CACHE_PATH = f'./cache/{SPACE_ID}_assets.json'
ASSET_FOLDER_CACHE_PATH = f'./cache/{SPACE_ID}_asset_folders.json'


def warn(slug, reason, *data):
    print(slug + ': ' + reason)
    with open('warnings.csv', 'a') as file:
        csv_writer = writer(file)
        csv_writer.writerow([slug, reason, *data])


def read_csv(file_path):
    print(f'loading {file_path}')
    with open(file_path, 'r') as file:
        return list(DictReader(file))


def load_json(file_path):
    print(f'loading {file_path}')
    with open(file_path, 'r') as file:
        return json.load(file)


def save_json(file_path, data):
    print(f'saving {file_path}')

    try:
        with open(file_path, 'w') as file:
            return json.dump(data, file, indent=2, ensure_ascii=True)
    except KeyboardInterrupt as e:
        print("KeyboardInterrupt: Saving file again!")
        save_json(file_path, data)
        raise e


def download_image(image_url, target_file_path):
    print(f'backing up asset {image_url!r} into {target_file_path!r}')

    response = requests.get(image_url, stream=True)

    if not response.ok:
        # TODO: do not continue
        print(f'Cannot download image {image_url}, got status code {response.status_code}')
        return

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

        response = requests.get(
            f'{BASE_URL}/v1/spaces/{SPACE_ID}{path}',
            headers=HEADERS,
            params=params
        )

        response.raise_for_status()
        response_data = response.json()

        if item_name not in response_data and isinstance(response_data, dict):
            raise KeyError(
                f'item_name {item_name!r} not in response. Possible keys {", ".join(response_data.keys())}'
            )

        new_items = response_data[item_name]

        page = None if len(new_items) < int(params['per_page']) else page + 1

        all_items.extend(new_items)

    return all_items


def is_asset_in_use(asset):
    file_path = asset['filename'].replace('https://s3.amazonaws.com/a.storyblok.com', '')

    response = requests.get(
        f'{BASE_URL}/v1/spaces/{SPACE_ID}/stories/',
        headers=HEADERS,
        params={
            'reference_search': file_path,
            'per_page': 1,
            'page': 1,
        }
    )

    response.raise_for_status()

    stories = response.json()['stories']

    return len(stories) != 0


def main():
    load_from_cache = True

    all_assets = None
    all_folders = None

    if load_from_cache:
        all_assets = load_json(ASSETS_CACHE_PATH)
        all_folders = load_json(ASSET_FOLDER_CACHE_PATH)
    else:
        all_assets = get_all_paginated('/assets', item_name='assets')
        all_folders = get_all_paginated('/asset_folders', item_name='asset_folders')

        save_json(ASSETS_CACHE_PATH, all_assets)
        save_json(ASSET_FOLDER_CACHE_PATH, all_folders)

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

    count = 0
    for asset in all_assets:
        if 'is_in_use' in asset:
            continue

        asset['is_in_use'] = is_asset_in_use(asset)

        count += 1

        if count % 20 == 0:
            save_json(ASSETS_CACHE_PATH, all_assets)

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

    folder_path_names_to_item_count = {}

    for asset in assets_not_in_use:
        path_name = folder_id_to_path_name[asset['asset_folder_id']]

        folder_path_names_to_item_count.setdefault(path_name, 0)

        folder_path_names_to_item_count[path_name] += 1

    print('Summary of files to be deleted')

    for path_name in sorted(folder_path_names_to_item_count.keys()):
        item_count = folder_path_names_to_item_count[path_name]
        print(f'{str(item_count).rjust(4, " ")} {path_name}')

    print()

    BLACKLISTED_FOLDER_PATHS = [
        '/Download Files',
        '/Downloads_NL',
        '/email assets',
        '/logos',
    ]

    BLACKLISTED_WORDS = [
        'mail',
        'logo',
    ]

    for asset in assets_not_in_use:
        id = asset["id"]

        asset_path_name = folder_id_to_path_name[asset['asset_folder_id']]
        if asset_path_name in BLACKLISTED_FOLDER_PATHS:
            print(f'Skipping {id} as it is in {asset_path_name}')
            continue

        if any(word in asset["filename"] for word in BLACKLISTED_WORDS):
            print(f'Skipping {id} as it contains blacklisted words')
            continue

        extension = pathlib.Path(asset["filename"]).suffix

        download_image(asset["filename"], f'./assets_backup/{SPACE_ID}/{id}{extension}')

        print(f'deleting asset {id}')

        response = requests.delete(
            f'{BASE_URL}/v1/spaces/{SPACE_ID}/assets/{id}',
            headers=HEADERS,
        )
        response.raise_for_status()

        asset['is_deleted'] = True

        save_json(ASSETS_CACHE_PATH, all_assets)

        pass


if __name__ == '__main__':
    main()

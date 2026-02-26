#!/usr/bin/env python3

import argparse
import json
import pathlib
import shutil
import sys
import time
from http import HTTPStatus
from os import getenv, makedirs, path

import requests

_REGION_TO_BASE_URLS = {
    "eu": "https://mapi.storyblok.com",
    "us": "https://api-us.storyblok.com",
    "ca": "https://api-ca.storyblok.com",
    "au": "https://api-ap.storyblok.com",
    "cn": "https://app.storyblokchina.cn",
}


class StoryblokClient:
    """
    Class that handles the storyblok client credentials as a global state.
    Useful in this script context but careful to not re-use (or import)
     this where the global state might affect your application.
    """

    _storyblok_space_id: str | None = None
    _storyblok_personal_access_token: str | None = None
    _storyblok_base_url: str | None = None

    DEFAULT_REGION = "eu"

    @classmethod
    def is_initialized(cls):
        return (
            cls._storyblok_space_id
            and cls._storyblok_personal_access_token
            and cls._storyblok_base_url
        )

    @classmethod
    def init_client(cls, space_id, token, region):
        if cls.is_initialized():
            raise RuntimeError("StoryblokClient already initialized")

        cls._storyblok_space_id = space_id
        cls._storyblok_personal_access_token = token
        cls._storyblok_base_url = _REGION_TO_BASE_URLS[region]

    @classmethod
    def request(cls, method, path, params=None, max_retries=3, base_delay=1.0, **kwargs):
        if not cls.is_initialized():
            raise RuntimeError("StoryblokClient not initialized")

        for attempt in range(max_retries + 1):
            try:
                # Add a small delay between requests to avoid rate limiting
                if attempt > 0:
                    # Exponential backoff
                    delay = base_delay * (2 ** (attempt - 1))
                    print(
                        f"Rate limited, waiting {delay:.1f} seconds before retry {attempt}/{max_retries}..."
                    )
                    time.sleep(delay)
                else:
                    # Small delay even on first request to be respectful
                    time.sleep(0.1)

                response = requests.request(
                    method,
                    f"{cls._storyblok_base_url}/v1/spaces/{cls._storyblok_space_id}{path}",
                    headers={
                        "Authorization": cls._storyblok_personal_access_token,
                    },
                    params=params,
                    timeout=30,
                    **kwargs,
                )

                # If we get a 429 (rate limited), retry
                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS.value:
                    if attempt < max_retries:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = float(retry_after)
                                print(f"Server requested wait of {delay} seconds")
                                time.sleep(delay)
                                continue
                            except ValueError:
                                pass
                        continue
                    # Last attempt failed, raise the error
                    response.raise_for_status()

                return response

            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    print(f"Request failed ({e}), retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    continue
                raise

        raise RuntimeError("Exceeded maximum retries for request")


def ensure_cache_dir_exists(cache_directory):
    if not path.exists(cache_directory):
        makedirs(cache_directory, exist_ok=True)


def load_json(file_path):
    print(f"Loading {file_path}")
    with open(file_path) as file:
        return json.load(file)


def save_json(file_path, data):
    try:
        with open(file_path, "w") as file:
            return json.dump(data, file, indent=2, ensure_ascii=True)
    except KeyboardInterrupt as e:
        print("KeyboardInterrupt: Saving file again to avoid corruption!")
        save_json(file_path, data)
        raise e


def backup_asset(
    asset_id,
    asset_url,
    space_id,
    backup_directory,
    continue_download_on_failure,
) -> str | None:
    extension = pathlib.Path(asset_url).suffix

    directory = path.join(
        backup_directory,
        space_id,
    )

    file_path = path.join(
        directory,
        f"{asset_id}{extension}",
    )

    if path.exists(file_path):
        print(f"Skipping download of {asset_url!r} as it was already backed-up to {file_path!r}")
        return file_path

    print(f"Downloading asset {asset_url!r} into {file_path!r}")

    makedirs(directory, exist_ok=True)

    response = requests.get(
        url=asset_url,
        stream=True,
        timeout=30,
    )

    if not response.ok:
        msg = f"Cannot download asset {asset_url}, got status code {response.status_code}"

        if continue_download_on_failure:
            print(msg)
            return None

        abort(
            f"{msg}. Use --continue-download-on-failure to ignore this error.",
        )

    with open(file_path, "wb") as out_file:
        shutil.copyfileobj(response.raw, out_file)
        return file_path


def get_all_paginated(path, item_name, params={}):
    page = 1

    all_items = []
    total_from_header = None
    previous_page_ids = None

    while page is not None:
        print(f"Getting {path}, page={page}")

        params = {
            "per_page": 100,
            **params,
            "page": page,
        }

        response = StoryblokClient.request("GET", path, params=params)

        response.raise_for_status()
        response_data = response.json()

        if total_from_header is None:
            total_raw = response.headers.get("total")
            if total_raw is not None:
                try:
                    total_from_header = int(total_raw)
                except (ValueError, TypeError):
                    pass

        if item_name not in response_data and isinstance(response_data, dict):
            raise KeyError(
                "item_name {!r} not in response. Possible keys {}".format(
                    item_name, ", ".join(response_data.keys())
                )
            )

        new_items = response_data[item_name]

        # Detect duplicate page (API returns same page for every request, e.g. /asset_folders).
        if page > 1 and previous_page_ids is not None:
            current_ids = {item.get("id") for item in new_items if item.get("id") is not None}
            if current_ids and current_ids == previous_page_ids:
                page = None
                break
        all_items.extend(new_items)
        previous_page_ids = {item.get("id") for item in new_items if item.get("id") is not None}

        if total_from_header is not None and len(all_items) >= total_from_header:
            page = None
        elif len(new_items) < int(params["per_page"]):
            page = None
        else:
            page = page + 1

    return all_items


def print_padded(*args):
    table_titles = [
        "Not in use",
        "To be deleted",
        "Path (use --ignore-path as is here to skip deletion)",
    ]

    outputs = args if args else table_titles

    print(
        " | ".join(
            [
                (
                    str(output).rjust(len(table_titles[index]), " ")
                    if isinstance(output, int)
                    else str(output).ljust(len(table_titles[index]), " ")
                )
                for index, output in enumerate(outputs)
            ]
        )
    )


def is_asset_in_use(asset):
    file_path = asset["filename"].split(".storyblok.com", 1)[1]
    response = StoryblokClient.request(
        "GET",
        "/stories",
        params={
            "reference_search": file_path,
            "per_page": 1,
            "page": 1,
        },
    )

    response.raise_for_status()

    stories = response.json()["stories"]
    return len(stories) != 0


def abort(message):
    print(message)
    sys.exit(1)


def _main():  # noqa: C901, PLR0915
    parser = argparse.ArgumentParser(
        description="storyblok-assets-cleanup an utility to delete unused assets."
    )

    parser.add_argument(
        "--token",
        type=str,
        default=getenv("STORYBLOK_PERSONAL_ACCESS_TOKEN"),
        required=getenv("STORYBLOK_PERSONAL_ACCESS_TOKEN") is None,
        help=(
            "Storyblok personal access token, "
            "alternatively use the env var STORYBLOK_PERSONAL_ACCESS_TOKEN."
        ),
    )
    parser.add_argument(
        "--space-id",
        type=str,
        default=getenv("STORYBLOK_SPACE_ID"),
        required=getenv("STORYBLOK_SPACE_ID") is None,
        help=("Storyblok space ID, alternatively use the env var STORYBLOK_SPACE_ID."),
    )
    parser.add_argument(
        "--region",
        type=str,
        default=StoryblokClient.DEFAULT_REGION,
        choices=list(_REGION_TO_BASE_URLS.keys()),
        help="Storyblok region (default: EU)",
    )
    parser.add_argument(
        "--delete",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="If we should delete assets, default to false.",
    )
    parser.add_argument(
        "--backup",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "If we should backup assets (to the directory specified in `--backup-directory`), "
            "defaults to true."
        ),
    )
    parser.add_argument(
        "--backup-directory",
        type=str,
        default="assets_backup",
        help="Backup directory, defaults to ./assets_backup.",
    )
    parser.add_argument(
        "--cache",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=("If we should use cache the assets index. Defaults to True (recommended)."),
    )
    parser.add_argument(
        "--cache-directory",
        type=str,
        default="cache",
        help="Cache directory, defaults to ./cache.",
    )
    parser.add_argument(
        "--continue-download-on-failure",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="If we should continue if the download of an asset fails. Defaults to true.",
    )
    parser.add_argument(
        "--ignore-path",
        type=str,
        action="append",
        required=False,
        default=[],
        help=(
            """
            Absolute filepaths that should be ignored, can be passed multiple times.
            Does not support prefixes, meaning you would need to pass the full path
            for each directory, as seen in the summary table
            (with starting slash and without trailing slash).
            Optional, defaults to no blacklisted paths.
            Example: --ignore-path '/Do not delete/emails' --ignore-path '/Do not delete/logos'.
            """
        ),
    )
    parser.add_argument(
        "--ignore-word",
        type=str,
        action="append",
        required=False,
        default=[],
        help=(
            "Will not delete assets which contains the specified words in its filename. "
            "Default to none/empty list."
        ),
    )

    args = parser.parse_args()

    StoryblokClient.init_client(args.space_id, args.token, args.region)

    should_delete_assets = args.delete
    use_cache = args.cache
    backup_assets = args.backup
    space_id = args.space_id
    continue_download_on_failure = args.continue_download_on_failure
    blacklisted_asset_directory_paths = args.ignore_path
    blacklisted_asset_filename_words = args.ignore_word
    cache_directory = args.cache_directory
    backup_directory = args.backup_directory
    assets_cache_path = path.join(cache_directory, f"{space_id}_assets.json")
    asset_folder_cache_path = path.join(cache_directory, f"{space_id}_asset_folders.json")

    for blacklisted_asset_folder_path in blacklisted_asset_directory_paths:
        if not blacklisted_asset_folder_path.startswith(
            "/"
        ) or blacklisted_asset_folder_path.endswith("/"):
            abort(
                f"Invalid blacklisted path {blacklisted_asset_folder_path!r}, "
                "expected a global Storyblok path starting with a slash and without trailing slash "
                "(ex: /sample/path). "
                "See --help for more information."
            )

    ensure_cache_dir_exists(cache_directory)

    all_assets = None
    all_folders = None

    if path.exists(assets_cache_path) and use_cache:
        all_assets = load_json(assets_cache_path)
    else:
        all_assets = get_all_paginated("/assets", item_name="assets")
        save_json(assets_cache_path, all_assets)

    if path.exists(asset_folder_cache_path) and use_cache:
        all_folders = load_json(asset_folder_cache_path)
    else:
        all_folders = get_all_paginated(
            "/asset_folders",
            item_name="asset_folders",
        )
        save_json(asset_folder_cache_path, all_folders)

    folder_ids_to_folder = {folder["id"]: folder for folder in all_folders}

    def get_folder_path_name(folder_id):
        folder = folder_ids_to_folder[folder_id]
        name = folder["name"]

        if folder["parent_id"] in [None, "", 0, "0"]:
            return f"/{name}"

        if folder["parent_id"] not in folder_ids_to_folder:
            print(
                f'Warning: Parent folder {folder["parent_id"]} of folder {folder["id"]} ("{name}")'
                "does not exist. Treating as root folder."
            )
            return f"/{name}"

        parent_path = get_folder_path_name(folder["parent_id"])

        return f"{parent_path}/{name}"

    def should_be_deleted(asset_path_name, filename):
        if asset_path_name in blacklisted_asset_directory_paths:
            print(f"Skipping {filename!r} as it is in {asset_path_name}")
            return False

        if any(word in filename for word in blacklisted_asset_filename_words if word):
            print(f"Skipping {filename!r} as it contains blacklisted words")
            return False

        return True

    print("Checking for assets in use. This might take a while.")

    count = 0
    for asset in all_assets:
        asset["to_be_deleted"] = False

        if "is_in_use" in asset:
            continue

        asset["is_in_use"] = is_asset_in_use(asset)

        count += 1

        if count % 25 == 0:
            print(f"{count}/{len(all_assets)}")
            save_json(assets_cache_path, all_assets)

    assets_not_in_use = [
        asset
        for asset in all_assets
        if not asset["is_in_use"] and not asset.get("is_deleted", False)
    ]

    folder_id_to_path_name = {
        folder["id"]: get_folder_path_name(folder["id"]) for folder in all_folders
    }

    folder_id_to_path_name[None] = "/"

    folder_path_names_to_item_counts = {}

    for asset in assets_not_in_use:
        asset_path_name = folder_id_to_path_name[asset["asset_folder_id"]]

        to_be_deleted = should_be_deleted(asset_path_name, asset["filename"])
        asset["to_be_deleted"] = to_be_deleted

        not_in_use_count, to_be_deleted_count = folder_path_names_to_item_counts.setdefault(
            asset_path_name, (0, 0)
        )

        folder_path_names_to_item_counts[asset_path_name] = (
            not_in_use_count + 1,
            to_be_deleted_count + 1 if to_be_deleted else to_be_deleted_count,
        )

    print("\nSummary of files to be deleted")

    print_padded()

    for path_name in sorted(folder_path_names_to_item_counts.keys()):
        not_in_use_count, to_be_deleted_count = folder_path_names_to_item_counts[path_name]

        print_padded(
            not_in_use_count,
            to_be_deleted_count,
            path_name,
        )

    print()

    if should_delete_assets:
        message = (
            "Do you really want to delete the assets after performing the backup? (y/n): "
            if backup_assets
            else "Do you really want to delete the assets? (y/n): "
        )
        should_delete_assets = input(message) == "y"

    elif backup_assets:
        input("Assets will not be deleted but will perform backup. Press any key to continue: ")

    else:
        input("Dry run mode: nothing will be done. Press any key to continue: ")

    for asset in assets_not_in_use:
        if not asset["to_be_deleted"]:
            print(f"Skipping asset {asset['id']} (matched ignore filter)")
            continue

        if backup_assets:
            if file_path := backup_asset(
                asset_id=asset["id"],
                asset_url=asset["filename"],
                space_id=space_id,
                backup_directory=backup_directory,
                continue_download_on_failure=continue_download_on_failure,
            ):
                asset["backed_up_to"] = file_path

        if should_delete_assets:
            print(f"Deleting asset {asset['id']}")

            response = StoryblokClient.request(
                "DELETE",
                f"/assets/{asset['id']}",
            )
            response.raise_for_status()

            asset["is_deleted"] = True

        else:
            print(
                f"Did not delete the asset {asset['id']!r}. To enable deletion use the --delete flag"
            )

        if backup_assets or should_delete_assets:
            save_json(assets_cache_path, all_assets)


def main():
    try:
        _main()
    except KeyboardInterrupt:
        print("\nInterrupted, exiting...")


if __name__ == "__main__":
    main()

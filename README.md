# [rentry.py](https://github.com/EtorixDev/rentry.py)
[![](https://img.shields.io/pypi/v/rentry.py.svg?style=flat-square&color=5677a6)](https://pypi.org/project/rentry.py/)
[![](https://img.shields.io/pypi/pyversions/rentry.py.svg?style=flat-square&color=5677a6)](https://pypi.org/project/rentry.py/)
[![](https://img.shields.io/pypi/dm/rentry.py.svg?style=flat-square&color=5677a6)](https://pypi.org/project/rentry.py/)
[![](https://img.shields.io/pypi/l/rentry.py.svg?style=flat-square&color=51a851)](https://pypi.org/project/rentry.py/)

A python wrapper for the rentry markdown service.

This package allows for accessing the [rentry](https://rentry.co/) API through the command line or as a module in your project.

- [Installation](#installation)
- [Command Line](#command-line)
- [Module](#module)
    - [Basic](#basic)
    - [Advanced](#advanced)
- [Auth Tokens](#auth-tokens)

## Installation
`rentry.py` can be installed via pip:
```
pip install rentry.py
```
Or added to your project via poetry:
```
poetry add rentry.py
```

## Command Line
The command interface offers every endpoint as terminal commands. Those commands and their arguments are detailed below.

### Commands
- `help`: Show this help message.
- `read`: Get the raw markdown of a page with a `SECRET_RAW_ACCESS_CODE` set or if you provide an `--auth-token`.
    - `rentry read <--page-id PAGE_ID> [--auth-token AUTH_TOKEN]`
- `fetch`: Fetch the data for a page you have the edit code for.
    - `rentry fetch <--page-id PAGE_ID> <--edit-code EDIT_CODE>`
- `exists`: Check if a page exists.
    - `rentry exists <--page-id PAGE_ID>`
- `create`: Create a new page.
    - `rentry create <--markdown MARKDOWN> [--page-id PAGE_ID] [--edit-code EDIT_CODE] [--metadata METADATA]`
- `update`: Update a page you have the edit or modify code for.
    - `rentry update <--page-id PAGE_ID> <--edit-code EDIT_CODE> [--new-page-id NEW_PAGE_ID] [--new-edit-code NEW_EDIT_CODE] [--new-modify-code NEW_MODIFY_CODE] [--markdown MARKDOWN] [--metadata METADATA] [--overwrite]`
- `delete`: Delete a page you have the edit code for.
    - `rentry delete <--page-id PAGE_ID> <--edit-code EDIT_CODE>`

### Arguments
- `--page-id`
- `--edit-code`
    - When used with the `update` command this can be a modify code instead.
    - Modify codes start with `m:` and do not allow updating the edit or modify codes or deleting the page.
- `--auth-token`
    - Auth tokens are acquired by contacting rentry support.
- `--new-page-id`
    - Must be between 2 and 100 characters.
    - Must contain only latin letters, numbers, underscores and hyphens.
    - Will cause the existing modify code to reset if set.
- `--new-edit-code`
    - Must be between 1 and 100 characters.
    - Can't start with `m:` as that is reserved for modify codes.
- `--new-modify-code`
    - Must start with `m:` and be between 1 and 100 characters.
    - Provide `m:` to remove the modify code.
- `--markdown`
    - Must be between 1 and 200,000 characters.
- `--metadata`
    - A JSON string containing `'{"string": "string"}'` key-value pairs.
- `--overwrite`
    - Whether to overwrite the existing markdown and metadata with the new values.
- `--base-url`
    - The base URL to use.
    - Defaults to `https://rentry.co` but can be set to `https://rentry.org`.
    - All data is shared between the two domains.

### Examples
- `rentry read --page-id py`
- `rentry fetch --page-id py --edit-code pyEditCode`
- `rentry exists --page-id py`
- `rentry create --markdown "Hello, World!" --page-id py --edit-code pyEditCode`
- `rentry delete --page-id py --edit-code pyEditCode --base-url "https://rentry.org"`

## Module
### Basic
The module interface offers every endpoint as methods: `read()`, `fetch()`, `exists()`, `create()`, `update()`, and `delete()`. The `read()` method is an alias of the `raw` endpoint and the `create()` method is an alias of the `new` endpoint.

Instantiate a synchronous or asynchronous client to get started with `rentry.py`.
```python
import asyncio

from rentry import RentryAsyncClient, RentryAsyncPage, RentrySyncClient, RentrySyncPage

sync_client = RentrySyncClient()
async_client = RentryAsyncClient()
```

You can customize the API base url by passing the client either `"https://rentry.co"` (default) or `"https://rentry.org"`. Both domains work the same and all data is shared between them.

If one isn't passed, a CSRF token will be generated automatically by requesting one from rentry and it will be stored in `csrf_token`. The headers returned by the API imply these CSRF tokens last one year. It's unclear if anything will void them before that cutoff, however a new one can be generated at any time by calling `client.refresh_session()`. Alternatively, if you would like to generate a new CSRF token on each request, which would end up doubling the number of requests in total, you can pass `use_session = False` to the client.

You can then call the endpoints directly on the clients.
```python
markdown: str = sync_client.read("py")
print(markdown)
# A python wrapper for the rentry markdown service.
```

Or, you can utilize the pages returned by `fetch()`, `create()`, and `update()`.
```python
py_page: RentrySyncPage = sync_client.fetch("py", "1234")
print(py_page.exists())
# True
py_page.delete()
print(py_page.exists())
# False
py_page.create()
print(py_page.exists())
# True

new_page: RentrySyncPage = sync_client.create("Hello, World!")
print(new_page.markdown)
# Hello, World!
print(new_page.page_url)
# https://rentry.co/<randomly_generated_string>
print(new_page.edit_code)
# <randomly_generated_string>
```

By default when you receive a `RentrySyncPage` or `RentryAsyncPage` their `stats` attribute will be empty. It's required to call `fetch()` to receive the extra page data. You can avoid doing this manually by passing `fetch = True` to `create()` or `update()`.
```python
print(new_page.stats.published_date)
# None
new_page.delete()
new_page.create(fetch = True)
print(new_page.stats.published_date)
# 2025-02-22 01:15:30
```

If you would like to identify yourself to the rentry API, you can do so by passing a `user_agent` to the client.
```python
sync_client = RentrySyncClient(user_agent = "My Cool Project")
```

This will make your request appear as `rentry.py/<version> (My Cool Project)` to the API.

This is not required and at this time it is unknown if rentry will even make use of this information in any way.

### Advanced
You can gain more control over your page style by making use of `RentryPageMetadata`. This is a mirror of the options listed at [rentry/metadata-how](https://rentry.co/metadata-how). You can also see a basic example of how metadata works at [rentry/metadata-example](https://rentry.co/metadata-example).

There are multiple ways to utilize the `RentryPageMetadata` object. The first is to build it through passing arguments. The second is through building it with a JSON string. The third is through building it with a dict.
```python
from rentry import RentryPageMetadata, RentrySyncClient, RentrySyncPage

sync_client = RentrySyncClient()
metadata_one = RentryPageMetadata(PAGE_TITLE="This is an example.")
metadata_two = RentryPageMetadata.build('{"PAGE_TITLE": "This is an example."}')
metadata_three = RentryPageMetadata.build({"PAGE_TITLE": "This is an example."})

page: RentrySyncPage = sync_client.create("Hello, World", metadata = metadata_one)
print(page.metadata.PAGE_TITLE)
# This is an example.
```

The validations done to the metadata are extensive. They can be found in the docstring or in the tutorial link above. Most of rentry's validations have been mirrored in the class, meaning if you attempt to use invalid metadata an error will be raised before sending a request to the API. There are two exceptions to this.

The first is `ACCESS_EASY_READ` which requires an existing rentry url as its value. Checking that would require an API call of its own, so the class simply doesn't check it before sending the request to the API. The API will send a non-200 response if the URL does not exist, so an error is raised then instead.

The second is `CONTENT_FONT` which requires an existing font on Google Fonts. It's possible to query the Google Fonts API, however rentry itself also does not validate fonts. If an invalid value is used here it will silently fail to load on the page.

## Auth Tokens
Auth tokens are how you access the `raw` endpoint through the `read()` method. No other endpoint requires auth tokens at this time.

You obtain an auth token by contacting rentry support with your request. There are two ways to make use of the auth token once acquired.

The first is through setting the `SECRET_RAW_ACCESS_CODE` metadata on a page. By doing so, anyone will be able to access the `raw` endpoint for your page. If you have an auth token, you can add it to your page like so: `SECRET_RAW_ACCESS_CODE = auth_token`. Once you save your changes the token will internally be obfuscated by rentry, so there is no need to worry about your token being stolen by someone else with edit access. However, as of 2025-02-22, there is a bug where if you save a `SECRET_RAW_ACCESS_CODE` to your page, even after you remove it users will be able to access the `raw` endpoint for your page. The only solution to stop it is to delete the page.

The second is by providing your auth token to the client as the `auth_token` argument. This will grant you access to any page's `raw` version regardless of if they have a `SECRET_RAW_ACCESS_CODE` set or not.
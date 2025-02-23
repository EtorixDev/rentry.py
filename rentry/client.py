from __future__ import annotations

import json
from datetime import datetime
from typing import Literal, Optional, cast

import httpx

from rentry.data import RENTRY_PAGE_URL_REGEX, USER_AGENT
from rentry.errors import RentryExistingPageError, RentryInvalidAuthTokenError, RentryInvalidContentLengthError, RentryInvalidCSRFError, RentryInvalidEditCodeError, RentryInvalidMetadataError, RentryInvalidPageURLError, RentryInvalidResponseError, RentryNonExistentPageError
from rentry.metadata import RentryPageMetadata, RentryPageStats


class RentryBase:
    """Base class for rentry API access."""

    def __init__(
        self,
        base_url: Literal["https://rentry.co", "https://rentry.org"] = "https://rentry.co",
        csrf_token: Optional[str] = None,
        auth_token: Optional[str] = None,
        user_agent: Optional[str] = None,
        use_session: bool = True,
    ) -> None:
        self.base_url: str = base_url.strip("/")
        self.csrf_token: Optional[str] = csrf_token
        self.auth_token: Optional[str] = auth_token
        self.user_agent: Optional[str] = user_agent
        self.use_session: bool = use_session

        if not csrf_token:
            self.refresh_session()

    @property
    def cookies(self) -> dict:
        """Cookies to be sent with every request. Only contains the CSRF token."""
        return {"csrftoken": self.csrf_token}

    @property
    def payload(self) -> dict:
        """Payload to be sent with every request. Only contains the CSRF token."""
        return {"csrfmiddlewaretoken": self.csrf_token}

    @property
    def headers(self) -> dict:
        """Headers to be sent with every request. Contains the Referer, rentry-auth, and User-Agent headers."""
        return {
            "Referer": self.base_url,
            "rentry-auth": self.auth_token if self.auth_token else "",
            "User-Agent": f"{USER_AGENT}" + (f" ({self.user_agent})" if self.user_agent else ""),
        }

    def refresh_session(self) -> str:
        """Refresh the CSRF token for this session.

        #### Returns
        - `str` — The new CSRF token. This is also automatically stored in the `csrf_token` attribute.
        """

        response: httpx.Response = httpx.get(self.base_url)
        self.csrf_token: Optional[str] = response.cookies["csrftoken"]
        return self.csrf_token

    def _verify_markdown(self, markdown: str, allow_empty: bool = False) -> str:
        markdown = markdown.strip()

        if not markdown:
            if not allow_empty:
                raise RentryInvalidContentLengthError("The markdown content is empty.")
        elif not 1 <= len(markdown) <= 200_000:
            raise RentryInvalidContentLengthError("The markdown content must be between 1 and 200,000 characters.")

        return markdown

    def _verify_page_id(self, page_id: str) -> str:
        page_id = page_id.split("/")[-1].strip()

        if not page_id:
            raise RentryInvalidPageURLError("The page URL is empty.")
        elif not 2 <= len(page_id) <= 100:
            raise RentryInvalidPageURLError(f'The page URL "{page_id}" is not between 2 and 100 characters.')
        elif not RENTRY_PAGE_URL_REGEX.match(page_id):
            raise RentryInvalidPageURLError(f'The page URL "{page_id}" is malformed.')

        return page_id

    def _verify_modify_code(self, modify_code: str) -> str:
        modify_code = modify_code.strip()

        if not modify_code:
            raise RentryInvalidEditCodeError("The modify code is empty.")
        elif not modify_code.lower().startswith("m:"):
            raise RentryInvalidEditCodeError('The modify code must start with "m:".')
        elif not 1 <= len(modify_code) <= 100:
            raise RentryInvalidEditCodeError(f'The modify code "{modify_code}" is not between 1 and 100 characters.')

        return modify_code

    def _verify_edit_code(self, edit_code: str) -> str:
        edit_code = edit_code.strip()

        if not edit_code:
            raise RentryInvalidEditCodeError("The edit code is empty.")
        elif edit_code.lower().startswith("m:"):
            raise RentryInvalidEditCodeError('The edit code cannot start with "m:" as it is reserved for modify codes.')
        elif not 1 <= len(edit_code) <= 100:
            raise RentryInvalidEditCodeError(f'The edit code "{edit_code}" is not between 1 and 100 characters.')

        return edit_code

    def _decipher_raw(self, res: httpx.Response) -> str:
        try:
            response_json: dict = res.json()
        except json.JSONDecodeError:
            raise RentryInvalidResponseError("The rentry API response was not JSON.")

        response_content: str = response_json.get("content", "")
        response_status: str = response_json.get("status", "")

        if response_status == "200":
            return response_content
        elif "This page does not have a SECRET_RAW_ACCESS_CODE set." in response_content:
            raise RentryInvalidAuthTokenError("The page does not have a SECRET_RAW_ACCESS_CODE set and you did not provide an auth_token.")
        elif "Value for SECRET_RAW_ACCESS_CODE not found." in response_content:
            raise RentryInvalidAuthTokenError("The auth_token provided is invalid. Ensure the value is correct and was provided by rentry support.")
        else:
            raise RentryInvalidResponseError(f"The rentry API returned a status code of {response_status}.")

    def _decipher_fetch(self, res: httpx.Response) -> dict:
        try:
            response_json: dict = res.json()
        except json.JSONDecodeError:
            raise RentryInvalidResponseError("The rentry API response was not JSON.")

        response_content = cast(dict, response_json.get("content", ""))
        response_errors = cast(str, response_json.get("errors", ""))
        response_status = cast(str, response_json.get("status", ""))

        if response_status == "200":
            return response_content
        elif "Invalid edit code" in response_errors:
            raise RentryInvalidEditCodeError("The edit code provided is invalid.")
        elif "does not exist" in response_content:
            raise RentryNonExistentPageError("The page does not exist.")
        else:
            raise RentryInvalidResponseError(f"The rentry API returned a status code of {response_status}.")

    def _decipher_exists(self, res: httpx.Response) -> bool:
        if "text/plain" in res.headers.get("content-type", ""):
            if res.text in ["True", "False"]:
                return res.text == "True"
            else:
                raise RentryInvalidResponseError("The rentry API response was not a boolean.")
        else:
            raise RentryInvalidResponseError("The rentry API response content type was not text/plain.")

    def _decipher_new(self, res: httpx.Response) -> dict:
        try:
            response_json: dict = res.json()
        except json.JSONDecodeError:
            raise RentryInvalidResponseError("The rentry API response was not JSON.")

        response_errors = cast(str, response_json.get("errors", ""))
        response_status = cast(str, response_json.get("status", ""))

        if response_status == "200":
            return {"url": response_json["url_short"], "edit_code": response_json["edit_code"]}
        elif "already in use" in response_errors:
            raise RentryExistingPageError("The page already exists.")
        elif "ACCESS_EASY_READ" in response_errors:
            if "Not a valid Rentry URL" in response_errors:
                raise RentryInvalidMetadataError("ACCESS_EASY_READ must be 300 characters or less and start with a forward slash or be the full rentry link (domain included).")
            elif "Rentry URL doesnt exist" in response_errors:
                raise RentryInvalidMetadataError("ACCESS_EASY_READ must be an existing rentry page.")
            else:
                raise RentryInvalidMetadataError("ACCESS_EASY_READ is invalid.")
        else:
            raise RentryInvalidResponseError(f"The rentry API returned a status code of {response_status}.")

    def _decipher_update(self, res: httpx.Response) -> bool:
        try:
            response_json: dict = res.json()
        except json.JSONDecodeError:
            raise RentryInvalidResponseError("The rentry API response was not JSON.")

        response_content = cast(str, response_json.get("content", ""))
        response_errors = cast(str, response_json.get("errors", ""))
        response_status = cast(str, response_json.get("status", ""))

        if response_status == "200":
            return True
        elif "Invalid edit code" in response_errors:
            raise RentryInvalidEditCodeError("The edit code provided is invalid.")
        elif "Invalid modify code" in response_errors:
            raise RentryInvalidEditCodeError("The modify code provided is invalid.")
        elif "does not exist" in response_content:
            raise RentryNonExistentPageError("The page does not exist.")
        elif "URL entered is the same" in response_errors:
            raise RentryExistingPageError("The new URL is the same as the old URL.")
        else:
            raise RentryInvalidResponseError(f"The rentry API returned a status code of {response_status}.")

    def _decipher_delete(self, res: httpx.Response) -> bool:
        try:
            response_json: dict = res.json()
        except json.JSONDecodeError:
            raise RentryInvalidResponseError("The rentry API response was not JSON.")

        response_content = cast(str, response_json.get("content", ""))
        response_errors = cast(str, response_json.get("errors", ""))
        response_status = cast(str, response_json.get("status", ""))

        if response_status == "200":
            return True
        elif "Invalid edit code" in response_errors:
            raise RentryInvalidEditCodeError("The edit code provided is invalid.")
        elif "does not exist" in response_content:
            raise RentryNonExistentPageError("The page does not exist.")
        else:
            raise RentryInvalidResponseError(f"The rentry API returned a status code of {response_status}.")


class RentrySyncClient(RentryBase):
    """---
    Provides synchronous access to the rentry API.

    #### Attributes
    - base_url: `Literal["https://rentry.co", "https://rentry.org"] = "https://rentry.co"` — The base URL for the API.
        - All data is shared between the two domains.
    - csrf_token: `Optional[str] = None` — The CSRF token for this session.
        - Automatically generated if not provided.
        - According to the headers returned by the rentry API, this should last for 1 year.
    - auth_token: `Optional[str] = None` — Your personal authentication token.
        - Only applicable for accessing the `/raw` version of a page.
        - If set as the `SECRET_RAW_ACCESS_CODE` metadata item on a page, anyone can access the `/raw`
            version of that page without setting this token.
        - If set as the `rentry-auth` header by passing it here, any page's `/raw` version can be accessed
            through the API.
        - Contact rentry support to request a token.
    - user_agent: `Optional[str] = None` — The User-Agent to be sent with every request to identify the client.
        - Appended in parentheses to the default User-Agent which consists of the package name and version.
    - use_session: `bool = True` — Whether to use the same CSRF token between requests.
        - If False, the session details will be refreshed before every request.
        - This will double the number of requests made to the rentry API.
        - Manually refresh the session with `refresh_session()`.

    #### Methods
    - `read()` — Get the raw content of a page.
        - Only available for pages with a `SECRET_RAW_ACCESS_CODE` set or for any page if you provide an `auth_token`.
        - Returns the plain text markdown content of the page.
    - `fetch()` — Fetch the data for a page.
        - Returns a page object with all the data for that page.
    - `exists()` — Check if a page exists.
        - Returns a boolean indicating whether the page exists.
    - `create()` — Create a new page.
        - A random URL and edit code are generated if not provided.
        - Returns a page object with the URL, edit code, markdown content, and optionally all of the data for that page.
    - `update()` — Update a page.
        - Requires the edit code when updating anything other than the markdown content, otherwise a modify code is allowed.
        - Returns a page object with whatever is provided, and optionally all of the data for that page.
    - `delete()` — Delete a page.
        - Returns True if the page was deleted successfully and raises an exception otherwise.
    - `refresh_session()` — Refreshes the CSRF token, cookies, and payload.

    #### Properties
    - cookies: `dict` — The cookies to be sent with every request. Only contains the CSRF token.
    - payload: `dict` — The payload to be sent with every request. Only contains the CSRF token.
    - headers: `dict` — The headers to be sent with every request. Contains the Referer and rentry-auth headers.
    """

    def __init__(
        self,
        base_url: Literal["https://rentry.co", "https://rentry.org"] = "https://rentry.co",
        csrf_token: Optional[str] = None,
        auth_token: Optional[str] = None,
        user_agent: Optional[str] = None,
        use_session: bool = True,
    ) -> None:
        super().__init__(base_url, csrf_token, auth_token, user_agent, use_session)

    def _get_response(self, method: str, endpoint: str, payload: Optional[dict] = None) -> httpx.Response:
        """Make a request to the rentry API and return the response."""
        if not self.use_session:
            self.refresh_session()
        if not self.csrf_token:
            raise RentryInvalidCSRFError("The CSRF token is invalid.")
        response: httpx.Response = httpx.request(method, f"{self.base_url}{endpoint}", headers=self.headers, cookies=self.cookies, data=payload)
        if response.status_code == 403:
            raise RentryInvalidCSRFError("The CSRF token is invalid.")
        elif response.status_code != 200:
            raise RentryInvalidResponseError(f"The rentry API returned a status code of {response.status_code}.")
        return response

    def read(self, page_id: str) -> str:
        """---
        Get the raw content of a page with a `SECRET_RAW_ACCESS_CODE` set or if you provide an `auth_token`.

        If you have a valid edit code, use `fetch()` and access the `markdown` attribute on the returned page object instead.

        #### Arguments
        - page_id: `str` — The page to get the raw content of.

        #### Returns
        - `str` — The raw content of the page.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidAuthTokenError` when the page does not have a `SECRET_RAW_ACCESS_CODE` set and you did not provide a valid `auth_token`.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        page_id = self._verify_page_id(page_id)
        response: str = self._decipher_raw(self._get_response("GET", f"/api/raw/{page_id}"))
        return response

    def fetch(self, page_id: str, edit_code: str) -> RentrySyncPage:
        """---
        Fetch the data for a page you have the edit code for.

        #### Arguments
        - page_id: `str` — The page to fetch.
        - edit_code: `str` — The edit code for the page.
            - May be a modify code instead.
            - Modify codes start with "m:" and do not allow updating the edit or modify codes or deleting the page.

        #### Returns
        - `RentrySyncPage` — The page object with all the data for that page.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryNonExistentPageError` when the page does not exist.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        is_modify_code: bool = edit_code.lower().startswith("m:")
        edit_code = self._verify_edit_code(edit_code) if not is_modify_code else self._verify_modify_code(edit_code)
        page_id = self._verify_page_id(page_id)
        payload: dict = {**self.payload, "edit_code": edit_code}
        response: dict = self._decipher_fetch(self._get_response("POST", f"/api/fetch/{page_id}", payload))
        page_id = response.get("url_case", "")
        markdown: str = response.get("text", "")
        modify_code_set: bool = response.get("modify_code_set", False)
        published_date: Optional[datetime] = datetime.fromisoformat(response.get("pub_date", "")) if response.get("pub_date", "") else None
        activated_date: Optional[datetime] = datetime.fromisoformat(response.get("activated_date", "")) if response.get("activated_date", "") else None
        edited_date: Optional[datetime] = datetime.fromisoformat(response.get("edit_date", "")) if response.get("edit_date", "") else None
        metadata: Optional[RentryPageMetadata] = RentryPageMetadata.build(response.get("metadata", {})) if response.get("metadata", {}) else None
        metadata_version: str = response.get("metadata_version", None)
        views: int = response.get("views", None)
        return RentrySyncPage(
            self,
            page_id,
            markdown,
            edit_code,
            None,
            metadata,
            RentryPageStats(
                modify_code_set,
                published_date,
                activated_date,
                edited_date,
                metadata_version,
                views,
            ),
        )

    def exists(self, page_id: str) -> bool:
        """---
        Check if a page exists.

        #### Arguments
        - page_id: `str` — The page to check the existence of.

        #### Returns
        - `bool` — Whether the page exists.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not "True" or "False".
        """

        page_id = self._verify_page_id(page_id)
        response: bool = self._decipher_exists(self._get_response("GET", f"/{page_id}/exists"))
        return response

    def create(self, markdown: str, page_id: Optional[str] = None, edit_code: Optional[str] = None, metadata: Optional[RentryPageMetadata] = None, fetch: bool = False) -> RentrySyncPage:
        """---
        Create a new page.

        #### Arguments
        - markdown: `str` — The markdown content of the page.
            - Must be between 1 and 200,000 characters.
        - page_id: `Optional[str] = None` — The ID of the page.
            - Must be between 2 and 100 characters.
            - Must contain only latin letters, numbers, underscores and hyphens.
            - If not provided, a random URL will be generated.
        - edit_code: `Optional[str] = None` — The edit code for the page.
            - Must be between 1 and 100 characters.
            - Can't start with "m:" as that is reserved for modify codes.
            - If not provided, a random edit code will be generated.
        - metadata: `Optional[RentryPageMetadata] = None` — The metadata for the page.
            - If not provided, no custom metadata will be set.
        - fetch: `bool = False` — Whether to automatically fetch the page data after creation.
            - If False, the extended details such as the exact creation date will not be available until you manually fetch the page.

        #### Returns
        - `RentrySyncPage` — The page object with the URL, edit code, markdown content, metadata, and optionally all of the extra data for that page.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryExistingPageError` when the page already exists.
        - `RentryInvalidContentLengthError` when the markdown content is an invalid length.
        - `RentryInvalidMetadataError` when the metadata is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        edit_code = self._verify_edit_code(edit_code) if edit_code else None
        page_id = self._verify_page_id(page_id) if page_id else None
        markdown = self._verify_markdown(markdown)
        payload: dict = {**self.payload, "text": markdown}
        if edit_code:
            payload["edit_code"] = edit_code
        if page_id:
            payload["url"] = page_id
        if metadata:
            payload["metadata"] = metadata.encode()
        response: dict[str, str] = self._decipher_new(self._get_response("POST", "/api/new", payload))
        page_id = response["url"]
        edit_code = response["edit_code"]
        return self.fetch(page_id, edit_code) if fetch else RentrySyncPage(self, page_id, markdown, edit_code, metadata=metadata)

    def update(self, page_id: str, edit_code: str, new_page_id: Optional[str] = None, new_edit_code: Optional[str] = None, new_modify_code: Optional[str] = None, markdown: Optional[str] = None, metadata: Optional[RentryPageMetadata] = None, overwrite: bool = False, fetch: bool = False) -> RentrySyncPage:
        """---
        Update a page you have the edit or modify code for.

        #### Arguments
        - page_id: `str` — The page to update.
        - edit_code: `str` — The edit code for the page.
            - May be a modify code instead.
            - Modify codes start with "m:" and do not allow updating the edit or modify codes or deleting the page.
        - new_page_id: `Optional[str] = None` — The new ID of the page.
            - Must be between 2 and 100 characters.
            - Must contain only latin letters, numbers, underscores and hyphens.
            - Will cause the existing modify code to reset if set.
        - new_edit_code: `Optional[str] = None` — The new edit code for the page.
            - Must be between 1 and 100 characters.
            - Can't start with "m:" as that is reserved for modify codes.
        - new_modify_code: `Optional[str] = None` — The new modify code for the page.
            - Must start with "m:" and be between 1 and 100 characters.
            - Provide "m:" to remove the modify code.
        - markdown: `Optional[str] = None` — The new markdown content of the page.
            - Must be between 1 and 200,000 characters.
        - metadata: `Optional[RentryPageMetadata] = None` — The new metadata for the page.
        - overwrite: `bool = False` — Whether to overwrite the existing markdown and metadata with the new values.
            - If False:
                - The new metadata will be merged with the existing metadata if provided, otherwise it will be left unchanged.
                - The new markdown content will overwrite the existing content if provided, otherwise it will be left unchanged.
            - If True:
                - The new metadata will replace the existing metadata if provided, otherwise it will be cleared.
                - The new markdown content will overwrite the existing content if provided, otherwise it will be cleared.
        - fetch: `bool = False` — Whether to automatically fetch the page data after updating.
            - If False, the extended details such as the exact creation date will not be available until you manually fetch the page.

        #### Returns
        - `RentrySyncPage` — The page object with the URL, edit code, markdown content, metadata, and optionally all of the extra data for that page.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryExistingPageError` when the new page URL is the same as the old page URL.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryInvalidEditCodeError` when the modify code is invalid.
        - `RentryInvalidContentLengthError` when the markdown content is an invalid length.
        - `RentryInvalidMetadataError` when the metadata is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        is_modify_code: bool = edit_code.lower().startswith("m:")
        if is_modify_code and (new_page_id or new_edit_code or new_modify_code):
            raise RentryInvalidEditCodeError("Modify codes can't be used to change the edit or modify codes.")
        edit_code = self._verify_edit_code(edit_code) if not is_modify_code else self._verify_modify_code(edit_code)
        new_page_id = self._verify_page_id(new_page_id) if new_page_id else None
        new_edit_code = self._verify_edit_code(new_edit_code) if new_edit_code else None
        new_modify_code = self._verify_modify_code(new_modify_code) if new_modify_code else None
        page_id = self._verify_page_id(page_id)
        markdown = self._verify_markdown(markdown, True) if markdown is not None else None
        payload: dict = {**self.payload, "edit_code": edit_code}
        if new_page_id:
            payload["new_url"] = new_page_id
        if new_edit_code:
            payload["new_edit_code"] = new_edit_code
        if new_modify_code:
            payload["new_modify_code"] = new_modify_code
        if markdown:
            payload["text"] = markdown
        if metadata:
            payload["metadata"] = metadata.encode()
        if not overwrite:
            payload["update_mode"] = "upsert"
        self._decipher_update(self._get_response("POST", f"/api/edit/{page_id}", payload))
        if fetch:
            updated_page: RentrySyncPage = self.fetch(new_page_id or page_id, new_edit_code or edit_code)
        else:
            updated_page: RentrySyncPage = RentrySyncPage(self, new_page_id or page_id, markdown, new_edit_code or edit_code, new_modify_code, metadata)
        updated_page.modify_code = new_modify_code
        return updated_page

    def delete(self, page_id: str, edit_code: str) -> RentrySyncPage:
        """---
        Delete a page you have the edit code for.

        #### Arguments
        - page_id: `str` — The page to delete.
        - edit_code: `str` — The edit code for the page.

        #### Returns
        - `RentrySyncPage` — An empty page object with the page ID set.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryNonExistentPageError` when the page does not exist.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        edit_code = self._verify_edit_code(edit_code)
        page_id = self._verify_page_id(page_id)
        payload: dict = {**self.payload, "edit_code": edit_code}
        self._decipher_delete(self._get_response("POST", f"/api/delete/{page_id}", payload))
        return RentrySyncPage(self, page_id)

    def __str__(self) -> str:
        return self.base_url

    def __repr__(self) -> str:
        return f"RentrySyncClient(base_url={repr(self.base_url)})"


class RentrySyncPage:
    """---
    Represents a page on rentry.

    #### Attributes
    - client: `RentrySyncClient` — The client used to access the rentry API.
    - page_id: `str` — The ID of the page.
    - markdown: `Optional[str]` — The markdown content of the page.
    - edit_code: `Optional[str]` — The edit code of the page.
    - modify_code: `Optional[str]` — The modify code of the page.
        - Only available when set manually via `update()`.
        - The `fetch()` method will not return this attribute.
    - modify_code_set: `Optional[bool]` — Whether the modify code is set.

    #### Properties
    - page_url: `str` — The URL of the page.

    #### Methods
    - `read()` — Get the raw content of the page.
        - Only available for pages with a `SECRET_RAW_ACCESS_CODE` set or for any page if you provide an `auth_token`.
        - Returns the plain text markdown content of the page.
    - `fetch()` — Fetch the data for a page.
        - Will update this page object with the most recent data.
    - `exists()` — Check if the page exists.
        - Returns a boolean indicating whether the page exists.
    - `create()` — Create this page if it does not exist.
        - Updates the edit code and markdown content, and optionally all of the data for this page.
    - `update()` — Update this page.
        - Requires the edit code be set when updating anything other than the content, otherwise a modify code is allowed.
        - Updates whatever is provided, and optionally all of the data for this page.
    - `delete()` — Delete this page.
        - Returns True if the page was deleted successfully and raises an exception otherwise.

    #### Raises
    - `RentryInvalidPageURLError` when the page ID is invalid.
    """

    def __init__(
        self,
        client: RentrySyncClient,
        page_id: str,
        markdown: Optional[str] = None,
        edit_code: Optional[str] = None,
        modify_code: Optional[str] = None,
        metadata: Optional[RentryPageMetadata] = None,
        stats: Optional[RentryPageStats] = None,
    ) -> None:
        self.client: RentrySyncClient = client
        self.page_id: str = self.client._verify_page_id(page_id)
        self.markdown: Optional[str] = markdown
        self.edit_code: Optional[str] = edit_code
        self.modify_code: Optional[str] = modify_code
        self.metadata: RentryPageMetadata = metadata or RentryPageMetadata()
        self.stats: RentryPageStats = stats or RentryPageStats()

    @property
    def page_url(self) -> str:
        """The URL of the page."""
        return f"{self.client.base_url}/{self.page_id}"

    def read(self) -> str:
        """---
        Get the raw content of the page if it has a `SECRET_RAW_ACCESS_CODE` set or if you provide an `auth_token`.

        If you set a valid edit code, use `fetch()` and access the `markdown` attribute instead.

        #### Returns
        - `str` — The raw content of the page.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidAuthTokenError` when the page does not have a `SECRET_RAW_ACCESS_CODE` set and you did not provide a valid `auth_token`.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        return self.client.read(self.page_id)

    def fetch(self) -> None:
        """---
        Fetch the data of the page if the edit code is set.

        #### Updates
        - This page object with the most recent data.
        - The `modify_code` attribute is not updated as the API does not return it.
            - If the API returns `False` for `modify_code_set`, the attribute is set to `None`.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryNonExistentPageError` when the page does not exist.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        page: RentrySyncPage = self.client.fetch(self.page_id, self.edit_code or self.modify_code or "")
        self.markdown = page.markdown
        self.edit_code = page.edit_code
        self.modify_code = None if page.stats and not page.stats.modify_code_set else self.modify_code
        self.stats = page.stats

    def exists(self) -> bool:
        """---
        Check if the page exists.

        #### Returns
        - `bool` — Whether the page exists.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not "True" or "False".
        """

        return self.client.exists(self.page_id)

    def create(self, fetch: bool = False) -> None:
        """---
        Create the page.

        #### Arguments
        - fetch: `bool = False` — Whether to automatically fetch the page data after creation.
            - If False, the extended details such as the exact creation date will not be available until you manually fetch the page.

        #### Updates
        - This page object with the most recent data.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryExistingPageError` when the page already exists.
        - `RentryInvalidContentLengthError` when the markdown content is an invalid length.
        - `RentryInvalidMetadataError` when the metadata is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        page: RentrySyncPage = self.client.create(self.markdown or "", self.page_id, self.edit_code, self.metadata, fetch)
        self.edit_code = page.edit_code
        self.modify_code = None
        self.markdown = page.markdown
        self.metadata = page.metadata
        self.stats = page.stats

    def update(self, new_page_id: Optional[str] = None, new_edit_code: Optional[str] = None, new_modify_code: Optional[str] = None, markdown: Optional[str] = None, metadata: Optional[RentryPageMetadata] = None, overwrite: bool = False, fetch: bool = False) -> None:
        """---
        Update the page if the edit or modify code is set. Modify codes do not allow updating the edit or modify codes or deleting the page.

        #### Arguments
        - new_page_id: `Optional[str] = None` — The new ID of the page.
            - Must be between 2 and 100 characters.
            - Must contain only latin letters, numbers, underscores and hyphens.
            - Will cause the existing modify code to reset if set.
        - new_edit_code: `Optional[str] = None` — The new edit code for the page.
            - Must be between 1 and 100 characters.
            - Can't start with "m:" as that is reserved for modify codes.
        - new_modify_code: `Optional[str] = None` — The new modify code for the page.
            - Must start with "m:" and be between 1 and 100 characters.
            - Provide "m:" to remove the modify code.
        - markdown: `Optional[str] = None` — The new markdown content of the page.
            - Must be between 1 and 200,000 characters.
        - metadata: `Optional[RentryPageMetadata] = None` — The new metadata for the page.
        - overwrite: `bool = False` — Whether to overwrite the existing markdown and metadata with the new values.
            - If False:
                - The new metadata will be merged with the existing metadata if provided, otherwise it will be left unchanged.
                - The new markdown content will overwrite the existing content if provided, otherwise it will be left unchanged.
            - If True:
                - The new metadata will replace the existing metadata if provided, otherwise it will be cleared.
                - The new markdown content will overwrite the existing content if provided, otherwise it will be cleared.
        - fetch: `bool = False` — Whether to automatically fetch the page data after updating.
            - If False, the extended details such as the exact creation date will not be available until you manually fetch the page.

        #### Updates
        - This page with whatever is provided.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryInvalidEditCodeError` when the modify code is invalid.
        - `RentryInvalidContentLengthError` when the markdown content is an invalid length.
        - `RentryInvalidMetadataError` when the metadata is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        page: RentrySyncPage = self.client.update(self.page_id, self.edit_code or "", new_page_id, new_edit_code, new_modify_code or self.modify_code, markdown, metadata, overwrite, fetch)
        self.page_id = page.page_id
        self.edit_code = page.edit_code
        self.modify_code = page.modify_code
        self.markdown = page.markdown
        self.metadata = page.metadata
        self.stats = page.stats

    def delete(self) -> None:
        """---
        Delete the page if the edit code is set. The only attribute that is cleared is `stats`.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryNonExistentPageError` when the page does not exist.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        self.stats = RentryPageStats()
        self.client.delete(self.page_id, self.edit_code or "")

    def __str__(self) -> str:
        return self.page_url

    def __repr__(self) -> str:
        return f"RentrySyncPage(page_id={repr(self.page_id)}, edit_code={repr(self.edit_code)})"


class RentryAsyncClient(RentryBase):
    """---
    Provides asynchronous access to the rentry API.

    #### Attributes
    - base_url: `Literal["https://rentry.co", "https://rentry.org"] = "https://rentry.co"` — The base URL for the API.
        - All data is shared between the two domains.
    - csrf_token: `Optional[str] = None` — The CSRF token for this session.
        - Automatically generated if not provided.
        - According to the headers returned by the rentry API, this should last for 1 year.
    - auth_token: `Optional[str] = None` — Your personal authentication token.
        - Only applicable for accessing the `/raw` version of a page.
        - If set as the `SECRET_RAW_ACCESS_CODE` metadata item on a page, anyone can access the `/raw`
            version of that page without setting this token.
        - If set as the `rentry-auth` header by passing it here, any page's `/raw` version can be accessed
            through the API.
        - Contact rentry support to request a token.
    - user_agent: `Optional[str] = None` — The User-Agent to be sent with every request to identify the client.
        - Appended in parentheses to the default User-Agent which consists of the package name and version.
    - use_session: `bool = True` — Whether to use the same CSRF token between requests.
        - If False, the session details will be refreshed before every request.
        - This will double the number of requests made to the rentry API.
        - Manually refresh the session with `refresh_session()`.

    #### Methods
    - `read()` — Get the raw content of a page.
        - Only available for pages with a `SECRET_RAW_ACCESS_CODE` set or for any page if you provide an `auth_token`.
        - Returns the plain text markdown content of the page.
    - `fetch()` — Fetch the data for a page.
        - Returns a page object with all the data for that page.
    - `exists()` — Check if a page exists.
        - Returns a boolean indicating whether the page exists.
    - `create()` — Create a new page.
        - A random URL and edit code are generated if not provided.
        - Returns a page object with the URL, edit code, markdown content, and optionally all of the data for that page.
    - `update()` — Update a page.
        - Requires the edit code when updating anything other than the markdown content, otherwise a modify code is allowed.
        - Returns a page object with whatever is provided, and optionally all of the data for that page.
    - `delete()` — Delete a page.
        - Returns True if the page was deleted successfully and raises an exception otherwise.
    - `refresh_session()` — Refreshes the CSRF token, cookies, and payload.

    #### Properties
    - cookies: `dict` — The cookies to be sent with every request. Only contains the CSRF token.
    - payload: `dict` — The payload to be sent with every request. Only contains the CSRF token.
    - headers: `dict` — The headers to be sent with every request. Contains the Referer and rentry-auth headers.
    """

    def __init__(
        self,
        base_url: Literal["https://rentry.co", "https://rentry.org"] = "https://rentry.co",
        csrf_token: Optional[str] = None,
        auth_token: Optional[str] = None,
        user_agent: Optional[str] = None,
        use_session: bool = True,
    ) -> None:
        super().__init__(base_url, csrf_token, auth_token, user_agent, use_session)

    async def _get_response(self, method: str, endpoint: str, payload: Optional[dict] = None) -> httpx.Response:
        """Make a request to the rentry API and return the response."""
        if not self.use_session:
            self.refresh_session()
        if not self.csrf_token:
            raise RentryInvalidCSRFError("The CSRF token is invalid.")
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.request(method, f"{self.base_url}{endpoint}", headers=self.headers, cookies=self.cookies, data=payload)
        if response.status_code == 403:
            raise RentryInvalidCSRFError("The CSRF token is invalid.")
        elif response.status_code != 200:
            raise RentryInvalidResponseError(f"The rentry API returned a status code of {response.status_code}.")
        return response

    async def read(self, page_id: str) -> str:
        """---
        Get the raw content of a page with a `SECRET_RAW_ACCESS_CODE` set or if you provide an `auth_token`.

        If you have a valid edit code, use `fetch()` and access the `markdown` attribute on the returned page object instead.

        #### Arguments
        - page_id: `str` — The page to get the raw content of.

        #### Returns
        - `str` — The raw content of the page.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidAuthTokenError` when the page does not have a `SECRET_RAW_ACCESS_CODE` set and you did not provide a valid `auth_token`.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        page_id = self._verify_page_id(page_id)
        response: str = self._decipher_raw(await self._get_response("GET", f"/api/raw/{page_id}"))
        return response

    async def fetch(self, page_id: str, edit_code: str) -> RentryAsyncPage:
        """---
        Fetch the data for a page you have the edit code for.

        #### Arguments
        - page_id: `str` — The page to fetch.
        - edit_code: `str` — The edit code for the page.
            - May be a modify code instead.
            - Modify codes start with "m:" and do not allow updating the edit or modify codes or deleting the page.

        #### Returns
        - `RentryAsyncPage` — The page object with all the data for that page.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryNonExistentPageError` when the page does not exist.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        is_modify_code: bool = edit_code.lower().startswith("m:")
        edit_code = self._verify_edit_code(edit_code) if not is_modify_code else self._verify_modify_code(edit_code)
        page_id = self._verify_page_id(page_id)
        payload: dict = {**self.payload, "edit_code": edit_code}
        response: dict = self._decipher_fetch(await self._get_response("POST", f"/api/fetch/{page_id}", payload))
        page_id = response.get("url_case", "")
        markdown: str = response.get("text", "")
        modify_code_set: bool = response.get("modify_code_set", False)
        published_date: Optional[datetime] = datetime.fromisoformat(response.get("pub_date", "")) if response.get("pub_date", "") else None
        activated_date: Optional[datetime] = datetime.fromisoformat(response.get("activated_date", "")) if response.get("activated_date", "") else None
        edited_date: Optional[datetime] = datetime.fromisoformat(response.get("edit_date", "")) if response.get("edit_date", "") else None
        metadata: Optional[RentryPageMetadata] = RentryPageMetadata.build(response.get("metadata", {})) if response.get("metadata", {}) else None
        metadata_version: str = response.get("metadata_version", None)
        views: int = response.get("views", None)
        return RentryAsyncPage(
            self,
            page_id,
            markdown,
            edit_code,
            None,
            metadata,
            RentryPageStats(
                modify_code_set,
                published_date,
                activated_date,
                edited_date,
                metadata_version,
                views,
            ),
        )

    async def exists(self, page_id: str) -> bool:
        """---
        Check if a page exists.

        #### Arguments
        - page_id: `str` — The page to check the existence of.

        #### Returns
        - `bool` — Whether the page exists.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not "True" or "False".
        """

        page_id = self._verify_page_id(page_id)
        response: bool = self._decipher_exists(await self._get_response("GET", f"/{page_id}/exists"))
        return response

    async def create(self, markdown: str, page_id: Optional[str] = None, edit_code: Optional[str] = None, metadata: Optional[RentryPageMetadata] = None, fetch: bool = False) -> RentryAsyncPage:
        """---
        Create a new page.

        #### Arguments
        - markdown: `str` — The markdown content of the page.
            - Must be between 1 and 200,000 characters.
        - page_id: `Optional[str] = None` — The ID of the page.
            - Must be between 2 and 100 characters.
            - Must contain only latin letters, numbers, underscores and hyphens.
            - If not provided, a random URL will be generated.
        - edit_code: `Optional[str] = None` — The edit code for the page.
            - Must be between 1 and 100 characters.
            - Can't start with "m:" as that is reserved for modify codes.
            - If not provided, a random edit code will be generated.
        - metadata: `Optional[RentryPageMetadata] = None` — The metadata for the page.
            - If not provided, no custom metadata will be set.
        - fetch: `bool = False` — Whether to automatically fetch the page data after creation.
            - If False, the extended details such as the exact creation date will not be available until you manually fetch the page.

        #### Returns
        - `RentryAsyncPage` — The page object with the URL, edit code, markdown content, metadata, and optionally all of the extra data for that page.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryExistingPageError` when the page already exists.
        - `RentryInvalidContentLengthError` when the markdown content is an invalid length.
        - `RentryInvalidMetadataError` when the metadata is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        edit_code = self._verify_edit_code(edit_code) if edit_code else None
        page_id = self._verify_page_id(page_id) if page_id else None
        markdown = self._verify_markdown(markdown)
        payload: dict = {**self.payload, "text": markdown}
        if edit_code:
            payload["edit_code"] = edit_code
        if page_id:
            payload["url"] = page_id
        if metadata:
            payload["metadata"] = metadata.encode()
        response: dict[str, str] = self._decipher_new(await self._get_response("POST", "/api/new", payload))
        page_id = response["url"]
        edit_code = response["edit_code"]
        return await self.fetch(page_id, edit_code) if fetch else RentryAsyncPage(self, page_id, markdown, edit_code, metadata=metadata)

    async def update(self, page_id: str, edit_code: str, new_page_id: Optional[str] = None, new_edit_code: Optional[str] = None, new_modify_code: Optional[str] = None, markdown: Optional[str] = None, metadata: Optional[RentryPageMetadata] = None, overwrite: bool = False, fetch: bool = False) -> RentryAsyncPage:
        """---
        Update a page you have the edit or modify code for.

        #### Arguments
        - page_id: `str` — The page to update.
        - edit_code: `str` — The edit code for the page.
            - May be a modify code instead.
            - Modify codes start with "m:" and do not allow updating the edit or modify codes or deleting the page.
        - new_page_id: `Optional[str] = None` — The new ID of the page.
            - Must be between 2 and 100 characters.
            - Must contain only latin letters, numbers, underscores and hyphens.
            - Will cause the existing modify code to reset if set.
        - new_edit_code: `Optional[str] = None` — The new edit code for the page.
            - Must be between 1 and 100 characters.
            - Can't start with "m:" as that is reserved for modify codes.
        - new_modify_code: `Optional[str] = None` — The new modify code for the page.
            - Must start with "m:" and be between 1 and 100 characters.
            - Provide "m:" to remove the modify code.
        - markdown: `Optional[str] = None` — The new markdown content of the page.
            - Must be between 1 and 200,000 characters.
        - metadata: `Optional[RentryPageMetadata] = None` — The new metadata for the page.
        - overwrite: `bool = False` — Whether to overwrite the existing markdown and metadata with the new values.
            - If False:
                - The new metadata will be merged with the existing metadata if provided, otherwise it will be left unchanged.
                - The new markdown content will overwrite the existing content if provided, otherwise it will be left unchanged.
            - If True:
                - The new metadata will replace the existing metadata if provided, otherwise it will be cleared.
                - The new markdown content will overwrite the existing content if provided, otherwise it will be cleared.
        - fetch: `bool = False` — Whether to automatically fetch the page data after updating.
            - If False, the extended details such as the exact creation date will not be available until you manually fetch the page.

        #### Returns
        - `RentryAsyncPage` — The page object with the URL, edit code, markdown content, metadata, and optionally all of the extra data for that page.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryExistingPageError` when the new page URL is the same as the old page URL.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryInvalidEditCodeError` when the modify code is invalid.
        - `RentryInvalidContentLengthError` when the markdown content is an invalid length.
        - `RentryInvalidMetadataError` when the metadata is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        is_modify_code: bool = edit_code.lower().startswith("m:")
        if is_modify_code and (new_page_id or new_edit_code or new_modify_code):
            raise RentryInvalidEditCodeError("Modify codes can't be used to change the edit or modify codes.")
        edit_code = self._verify_edit_code(edit_code) if not is_modify_code else self._verify_modify_code(edit_code)
        new_page_id = self._verify_page_id(new_page_id) if new_page_id else None
        new_edit_code = self._verify_edit_code(new_edit_code) if new_edit_code else None
        new_modify_code = self._verify_modify_code(new_modify_code) if new_modify_code else None
        page_id = self._verify_page_id(page_id)
        markdown = self._verify_markdown(markdown, True) if markdown is not None else None
        payload: dict = {**self.payload, "edit_code": edit_code}
        if new_page_id:
            payload["new_url"] = new_page_id
        if new_edit_code:
            payload["new_edit_code"] = new_edit_code
        if new_modify_code:
            payload["new_modify_code"] = new_modify_code
        if markdown:
            payload["text"] = markdown
        if metadata:
            payload["metadata"] = metadata.encode()
        if not overwrite:
            payload["update_mode"] = "upsert"
        self._decipher_update(await self._get_response("POST", f"/api/edit/{page_id}", payload))
        if fetch:
            updated_page: RentryAsyncPage = await self.fetch(new_page_id or page_id, new_edit_code or edit_code)
        else:
            updated_page: RentryAsyncPage = RentryAsyncPage(self, new_page_id or page_id, markdown, new_edit_code or edit_code, new_modify_code, metadata)
        updated_page.modify_code = new_modify_code
        return updated_page

    async def delete(self, page_id: str, edit_code: str) -> RentryAsyncPage:
        """---
        Delete a page you have the edit code for.

        #### Arguments
        - page_id: `str` — The page to delete.
        - edit_code: `str` — The edit code for the page.

        #### Returns
        - `RentryAsyncPage` — An empty page object with the page ID set.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryNonExistentPageError` when the page does not exist.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        edit_code = self._verify_edit_code(edit_code)
        page_id = self._verify_page_id(page_id)
        payload: dict = {**self.payload, "edit_code": edit_code}
        self._decipher_delete(await self._get_response("POST", f"/api/delete/{page_id}", payload))
        return RentryAsyncPage(self, page_id)

    def __str__(self) -> str:
        return self.base_url

    def __repr__(self) -> str:
        return f"RentrySyncClient(base_url={repr(self.base_url)})"


class RentryAsyncPage:
    """---
    Represents a page on rentry.

    #### Attributes
    - client: `RentrySyncClient` — The client used to access the rentry API.
    - page_id: `str` — The ID of the page.
    - markdown: `Optional[str]` — The markdown content of the page.
    - edit_code: `Optional[str]` — The edit code of the page.
    - modify_code: `Optional[str]` — The modify code of the page.
        - Only available when set manually via `update()`.
        - The `fetch()` method will not return this attribute.
    - modify_code_set: `Optional[bool]` — Whether the modify code is set.

    #### Properties
    - page_url: `str` — The URL of the page.

    #### Methods
    - `read()` — Get the raw content of the page.
        - Only available for pages with a `SECRET_RAW_ACCESS_CODE` set or for any page if you provide an `auth_token`.
        - Returns the plain text markdown content of the page.
    - `fetch()` — Fetch the data for a page.
        - Will update this page object with the most recent data.
    - `exists()` — Check if the page exists.
        - Returns a boolean indicating whether the page exists.
    - `create()` — Create this page if it does not exist.
        - Updates the edit code and markdown content, and optionally all of the data for this page.
    - `update()` — Update this page.
        - Requires the edit code be set when updating anything other than the content, otherwise a modify code is allowed.
        - Updates whatever is provided, and optionally all of the data for this page.
    - `delete()` — Delete this page.
        - Returns True if the page was deleted successfully and raises an exception otherwise.

    #### Raises
    - `RentryInvalidPageURLError` when the page ID is invalid.
    """

    def __init__(
        self,
        client: RentryAsyncClient,
        page_id: str,
        markdown: Optional[str] = None,
        edit_code: Optional[str] = None,
        modify_code: Optional[str] = None,
        metadata: Optional[RentryPageMetadata] = None,
        stats: Optional[RentryPageStats] = None,
    ) -> None:
        self.client: RentryAsyncClient = client
        self.page_id: str = self.client._verify_page_id(page_id)
        self.markdown: Optional[str] = markdown
        self.edit_code: Optional[str] = edit_code
        self.modify_code: Optional[str] = modify_code
        self.metadata: RentryPageMetadata = metadata or RentryPageMetadata()
        self.stats: RentryPageStats = stats or RentryPageStats()

    @property
    def page_url(self) -> str:
        """The URL of the page."""
        return f"{self.client.base_url}/{self.page_id}"

    async def read(self) -> str:
        """---
        Get the raw content of the page if it has a `SECRET_RAW_ACCESS_CODE` set or if you provide an `auth_token`.

        If you set a valid edit code, use `fetch()` and access the `markdown` attribute instead.

        #### Returns
        - `str` — The raw content of the page.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidAuthTokenError` when the page does not have a `SECRET_RAW_ACCESS_CODE` set and you did not provide a valid `auth_token`.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        return await self.client.read(self.page_id)

    async def fetch(self) -> None:
        """---
        Fetch the data of the page if the edit code is set.

        #### Updates
        - This page object with the most recent data.
        - The `modify_code` attribute is not updated as the API does not return it.
            - If the API returns `False` for `modify_code_set`, the attribute is set to `None`.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryNonExistentPageError` when the page does not exist.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        page: RentryAsyncPage = await self.client.fetch(self.page_id, self.edit_code or self.modify_code or "")
        self.markdown = page.markdown
        self.edit_code = page.edit_code
        self.modify_code = None if page.stats and not page.stats.modify_code_set else self.modify_code
        self.stats = page.stats

    async def exists(self) -> bool:
        """---
        Check if the page exists.

        #### Returns
        - `bool` — Whether the page exists.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not "True" or "False".
        """

        return await self.client.exists(self.page_id)

    async def create(self, fetch: bool = False) -> None:
        """---
        Create the page.

        #### Arguments
        - fetch: `bool = False` — Whether to automatically fetch the page data after creation.
            - If False, the extended details such as the exact creation date will not be available until you manually fetch the page.

        #### Updates
        - This page object with the most recent data.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryExistingPageError` when the page already exists.
        - `RentryInvalidContentLengthError` when the markdown content is an invalid length.
        - `RentryInvalidMetadataError` when the metadata is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        page: RentryAsyncPage = await self.client.create(self.markdown or "", self.page_id, self.edit_code, self.metadata, fetch)
        self.edit_code = page.edit_code
        self.modify_code = None
        self.markdown = page.markdown
        self.metadata = page.metadata
        self.stats = page.stats

    async def update(self, new_page_id: Optional[str] = None, new_edit_code: Optional[str] = None, new_modify_code: Optional[str] = None, markdown: Optional[str] = None, metadata: Optional[RentryPageMetadata] = None, overwrite: bool = False, fetch: bool = False) -> None:
        """---
        Update the page if the edit or modify code is set. Modify codes do not allow updating the edit or modify codes or deleting the page.

        #### Arguments
        - new_page_id: `Optional[str] = None` — The new ID of the page.
            - Must be between 2 and 100 characters.
            - Must contain only latin letters, numbers, underscores and hyphens.
            - Will cause the existing modify code to reset if set.
        - new_edit_code: `Optional[str] = None` — The new edit code for the page.
            - Must be between 1 and 100 characters.
            - Can't start with "m:" as that is reserved for modify codes.
        - new_modify_code: `Optional[str] = None` — The new modify code for the page.
            - Must start with "m:" and be between 1 and 100 characters.
            - Provide "m:" to remove the modify code.
        - markdown: `Optional[str] = None` — The new markdown content of the page.
            - Must be between 1 and 200,000 characters.
        - metadata: `Optional[RentryPageMetadata] = None` — The new metadata for the page.
        - overwrite: `bool = False` — Whether to overwrite the existing markdown and metadata with the new values.
            - If False:
                - The new metadata will be merged with the existing metadata if provided, otherwise it will be left unchanged.
                - The new markdown content will overwrite the existing content if provided, otherwise it will be left unchanged.
            - If True:
                - The new metadata will replace the existing metadata if provided, otherwise it will be cleared.
                - The new markdown content will overwrite the existing content if provided, otherwise it will be cleared.
        - fetch: `bool = False` — Whether to automatically fetch the page data after updating.
            - If False, the extended details such as the exact creation date will not be available until you manually fetch the page.

        #### Updates
        - This page with whatever is provided.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryInvalidEditCodeError` when the modify code is invalid.
        - `RentryInvalidContentLengthError` when the markdown content is an invalid length.
        - `RentryInvalidMetadataError` when the metadata is invalid.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        page: RentryAsyncPage = await self.client.update(self.page_id, self.edit_code or "", new_page_id, new_edit_code, new_modify_code or self.modify_code, markdown, metadata, overwrite, fetch)
        self.page_id = page.page_id
        self.edit_code = page.edit_code
        self.modify_code = page.modify_code
        self.markdown = page.markdown
        self.metadata = page.metadata
        self.stats = page.stats

    async def delete(self) -> None:
        """---
        Delete the page if the edit code is set. The only attribute that is cleared is `stats`.

        #### Raises
        - `RentryInvalidPageURLError` when the page URL is invalid.
        - `RentryInvalidEditCodeError` when the edit code is invalid.
        - `RentryNonExistentPageError` when the page does not exist.
        - `RentryInvalidResponseError` when the response from the rentry API is not JSON or is an error response.
        - `RentryInvalidCSRFError` when the CSRF token is invalid.
        """

        self.stats = RentryPageStats()
        await self.client.delete(self.page_id, self.edit_code or "")

    def __str__(self) -> str:
        return self.page_url

    def __repr__(self) -> str:
        return f"RentryAsyncPage(page_id={repr(self.page_id)}, edit_code={repr(self.edit_code)})"

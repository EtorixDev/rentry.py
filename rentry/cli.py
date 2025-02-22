from argparse import ArgumentParser
from typing import Optional

from rentry.client import RentrySyncClient, RentrySyncPage
from rentry.errors import RentryExistingPageError, RentryInvalidAuthTokenError, RentryInvalidContentLengthError, RentryInvalidCSRFError, RentryInvalidEditCodeError, RentryInvalidMetadataError, RentryInvalidPageURLError, RentryInvalidResponseError, RentryNonExistentPageError
from rentry.metadata import RentryPageMetadata

USAGE = """
Command line access to the rentry API.

#### Commands
- help: Show this help message.
- read: Get the raw content of a page with a SECRET_RAW_ACCESS_CODE set or if you provide an --auth-token.
    - Required: --page-id
    - Optional: --auth-token
        - Auth tokens are acquired by contacting rentry support.
- fetch: Fetch the data for a page you have the edit code for.
    - Required: --page-id
    - Required: --edit-code
- exists: Check if a page exists.
    - Required: --page-id
- create: Create a new page.
    - Required: --content
        - Must be between 1 and 200,000 characters.
    - Optional: --page-id
        - Must be between 2 and 100 characters.
        - Must contain only latin letters, numbers, underscores and hyphens.
        - If not provided, a random URL will be generated.
    - Optional: --edit-code
        - Must be between 1 and 100 characters.
        - Can't start with "m:" as that is reserved for modify codes.
        - If not provided, a random edit code will be generated.
    - Optional: --metadata
        - A JSON string containing "string": "string" key-value pairs.
- delete: Delete a page you have the edit code for.
    - Required: --page-id
    - Required: --edit-code

#### Examples
- rentry read --page-id py
- rentry fetch --page-id py --edit-code pyEditCode
- rentry exists --page-id py
- rentry create --content "Hello, World!" --page-id py --edit-code pyEditCode
- rentry delete --page-id py --edit-code pyEditCode
"""


def main() -> None:
    client: RentrySyncClient = RentrySyncClient()
    parser: ArgumentParser = ArgumentParser(prog="rentry", usage=USAGE, description="Access the rentry API through the command line.")
    parser.add_argument("command", type=str, nargs="?", help="The command to run.")
    parser.add_argument("--page-id", type=str, help="The page ID to use.")
    parser.add_argument("--edit-code", type=str, help="The edit code to use.")
    parser.add_argument("--auth-token", type=str, help="The auth token to use.")
    parser.add_argument("--content", type=str, help="The content to use.")
    parser.add_argument("--metadata", type=str, help="The metadata to use.")

    try:
        args: dict = vars(parser.parse_args())
        command: Optional[str] = args.get("command")
        page_id: Optional[str] = args.get("page_id")
        edit_code: Optional[str] = args.get("edit_code")
        auth_token: Optional[str] = args.get("auth_token")
        content: Optional[str] = args.get("content")
        metadata: Optional[RentryPageMetadata] = RentryPageMetadata.build(mtdt) if (mtdt := args.get("metadata")) else None

        if not command or command == "help":
            print(USAGE)
        elif command == "read":
            if not page_id:
                print("You must provide a page ID with the --page-id argument.")
                return

            client.auth_token = auth_token
            markdown: str = client.read(page_id)
            print(markdown)
        elif command == "fetch":
            if not page_id or not edit_code:
                print("You must provide a page ID with the --page-id argument and an edit code (or modify code) with the --edit-code argument.")
                return

            page: RentrySyncPage = client.fetch(page_id, edit_code)
            modify_code_set: Optional[str] = f"    |-- Modify Code Set: {page.stats.modify_code_set}" if page.stats else None
            published_date: Optional[str] = f"    |--- Published Date: {page.stats.published_date.strftime('%B %d, %Y %H:%M:%S')}" if page.stats and page.stats.published_date else None
            activated_date: Optional[str] = f"    |--- Activated Date: {page.stats.activated_date.strftime('%B %d, %Y %H:%M:%S')}" if page.stats and page.stats.activated_date else None
            edited_date: Optional[str] = f"    |------ Edited Date: {page.stats.edited_date.strftime('%B %d, %Y %H:%M:%S')}" if page.stats and page.stats.edited_date else None
            metadata_version: Optional[str] = f"    |- Metadata Version: {page.stats.metadata_version}" if page.stats else None
            view_count: Optional[str] = f"    |------- View Count: {page.stats.views}" if page.stats else None
            stats: str = "\n" + "\n".join([stat for stat in [modify_code_set, published_date, activated_date, edited_date, metadata_version, view_count] if stat])
            stats = stats if stats.strip() else "No stats available."
            print(f" Page URL: {page.page_url}\nEdit Code: {page.edit_code}\n    Stats: {stats}\n Markdown: \n\n{page.markdown}")
        elif command == "exists":
            if not page_id:
                print("You must provide a page ID with the --page-id argument.")
                return

            exists: bool = client.exists(page_id)
            print(exists)
        elif command == "create":
            if not content:
                print("You must provide content with the --content argument.")
                return

            page: RentrySyncPage = client.create(content, page_id, edit_code, metadata)
            print(f" Page URL: {page.page_url}\nEdit Code: {page.edit_code}\n Markdown: \n\n{page.markdown}")
        elif command == "delete":
            if not page_id or not edit_code:
                print("You must provide a page ID with the --page-id argument and an edit code with the --edit-code argument.")
                return

            page: RentrySyncPage = client.delete(page_id, edit_code)
            print(f"{page.page_url} has been deleted.")
    except (RentryExistingPageError, RentryInvalidAuthTokenError, RentryInvalidContentLengthError, RentryInvalidCSRFError, RentryInvalidEditCodeError, RentryInvalidMetadataError, RentryInvalidPageURLError, RentryInvalidResponseError, RentryNonExistentPageError) as e:
        print(str(e).replace("auth_token", "--auth-token"))
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()

import sys
from argparse import ArgumentParser
from typing import Any, NoReturn, Optional, cast

from rentry.client import RentrySyncClient, RentrySyncPage
from rentry.errors import (
    RentryExistingPageError,
    RentryInvalidAuthTokenError,
    RentryInvalidContentLengthError,
    RentryInvalidCSRFError,
    RentryInvalidEditCodeError,
    RentryInvalidMetadataError,
    RentryInvalidPageURLError,
    RentryInvalidResponseError,
    RentryNonExistentPageError,
)
from rentry.metadata import RentryPageMetadata

USAGE = """
Command line access to the rentry API.

#### Commands
- help: Show this help message.
- read: Get the raw markdown of a page with a SECRET_RAW_ACCESS_CODE set or if you provide an --auth-token.
    - rentry read <--page-id PAGE_ID> [--auth-token AUTH_TOKEN]
- fetch: Fetch the data for a page you have the edit code for.
    - rentry fetch <--page-id PAGE_ID> <--edit-code EDIT_CODE>
- exists: Check if a page exists.
    - rentry exists <--page-id PAGE_ID>
- create: Create a new page.
    - rentry create <--markdown MARKDOWN> [--page-id PAGE_ID] [--edit-code EDIT_CODE] [--metadata METADATA]
- update: Update a page you have the edit or modify code for.
    - rentry update <--page-id PAGE_ID> <--edit-code EDIT_CODE> [--new-page-id NEW_PAGE_ID] [--new-edit-code NEW_EDIT_CODE] [--new-modify-code NEW_MODIFY_CODE] [--markdown MARKDOWN] [--metadata METADATA] [--overwrite]
- delete: Delete a page you have the edit code for.
    - rentry delete <--page-id PAGE_ID> <--edit-code EDIT_CODE>

#### Arguments
--page-id
--edit-code
    - When used with the "update" command this can be a modify code instead.
    - Modify codes start with "m:" and do not allow updating the edit or modify codes or deleting the page.
--auth-token
    - Auth tokens are acquired by contacting rentry support.
--new-page-id
    - Must be between 2 and 100 characters.
    - Must contain only latin letters, numbers, underscores and hyphens.
    - Will cause the existing modify code to reset if set.
--new-edit-code
    - Must be between 1 and 100 characters.
    - Can't start with "m:" as that is reserved for modify codes.
--new-modify-code
    - Must start with "m:" and be between 1 and 100 characters.
    - Provide "m:" to remove the modify code.
--markdown
    - Must be between 1 and 200,000 characters.
--metadata
    - A JSON string containing '{"string": "string"}' key-value pairs.
--overwrite
    - Whether to overwrite the existing markdown and metadata with the new values.
--base-url
    - The base URL to use.
    - Defaults to "https://rentry.co" but can be set to "https://rentry.org".
    - All data is shared between the two domains.

#### Examples
- rentry read --page-id py
- rentry fetch --page-id py --edit-code pyEditCode
- rentry exists --page-id py
- rentry create --markdown "Hello, World!" --page-id py --edit-code pyEditCode
- rentry update --page-id py --edit-code pyEditCode --metadata '{"PAGE_TITLE": "Hello, World!"}' --overwrite
- rentry delete --page-id py --edit-code pyEditCode
"""


class RentryArgumentParser(ArgumentParser):
    def error(self, message) -> NoReturn:
        if "unrecognized arguments" in message:
            print('Unrecognized arguments. Use "rentry help" for more information.')
        elif all([term in message for term in ["invalid choice", "--base-url"]]):
            print('Invalid choice for --base-url. Use "rentry help" for more information.')
        else:
            print(message)
        sys.exit(2)


def main() -> None:
    client: RentrySyncClient = RentrySyncClient()
    parser: ArgumentParser = RentryArgumentParser(prog="rentry", usage=USAGE, description="Access the rentry API through the command line.")
    parser.add_argument("command", type=str, nargs="?", help="The command to run.")
    parser.add_argument("--page-id", type=str, help="The page ID to use.")
    parser.add_argument("--edit-code", type=str, help="The edit code to use.")
    parser.add_argument("--auth-token", type=str, help="The auth token to use.")
    parser.add_argument("--new-page-id", type=str, help="The new page ID to use.")
    parser.add_argument("--new-edit-code", type=str, help="The new edit code to use.")
    parser.add_argument("--new-modify-code", type=str, help="The new modify code to use.")
    parser.add_argument("--markdown", type=str, help="The markdown to use.")
    parser.add_argument("--metadata", type=str, help="The metadata to use.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Whether to overwrite the existing markdown and metadata with the new values.",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="https://rentry.co",
        choices=["https://rentry.co", "https://rentry.org"],
        help="The base URL to use.",
    )

    try:
        args: dict[str, Any] = vars(parser.parse_args())
        command: Optional[str] = args.get("command")
        page_id: Optional[str] = cast(str, pid).split("/")[-1].strip() if (pid := args.get("page_id")) is not None else None
        edit_code: Optional[str] = args.get("edit_code")
        auth_token: Optional[str] = args.get("auth_token")
        new_page_id: Optional[str] = args.get("new_page_id")
        new_edit_code: Optional[str] = args.get("new_edit_code")
        new_modify_code: Optional[str] = args.get("new_modify_code")
        markdown: Optional[str] = args.get("markdown")
        metadata: Optional[RentryPageMetadata] = RentryPageMetadata.build(mtdt) if (mtdt := args.get("metadata")) else None
        overwrite: bool = args.get("overwrite") or False
        base_url: str = args.get("base_url") or "https://rentry.co"

        if not command or command == "help":
            print(USAGE)
        elif command == "read":
            if not page_id:
                print("You must provide a page ID with the --page-id argument.")
                return
            elif edit_code or new_page_id or new_edit_code or new_modify_code or markdown or metadata or overwrite:
                print('More arguments than expected for the "read" command. Use "rentry help" for more information.')
                return

            client.auth_token = auth_token
            markdown = client.read(page_id)
            print(markdown)
        elif command == "fetch":
            if not page_id or not edit_code:
                print("You must provide a page ID with the --page-id argument and an edit code (or modify code) with the --edit-code argument.")
                return
            elif auth_token or new_page_id or new_edit_code or new_modify_code or markdown or metadata or overwrite:
                print('More arguments than expected for the "fetch" command. Use "rentry help" for more information.')
                return

            page: RentrySyncPage = client.fetch(page_id, edit_code)
            is_modify_code: bool = edit_code.lower().startswith("m:")
            f_out_page_id: str = f"├───── Page ID: {page.page_id}"
            f_out_edit_code: Optional[str] = f"├─── Edit Code: {edit_code}" if not is_modify_code else None
            f_out_modify_code: Optional[str] = f"├─ Modify Code: {edit_code}" if is_modify_code else None
            f_out_stats: Optional[str] = "├─────── Stats:" if page.stats else None
            f_out_metadata: str = f"├──── Metadata: {page.metadata.encode()}" if bool(page.metadata) else "├──── Metadata: None"
            f_out_markdown: Optional[str] = f"├──── Markdown:─┐\n                ↓\n{page.markdown}" if page.markdown else "├──── Markdown: None"

            f_out_modify_code_set: Optional[str] = f"│        ├── Modify Code Set: {page.stats.modify_code_set}" if page.stats else None
            f_out_published_date: Optional[str] = (
                f"│        ├─── Published Date: {page.stats.published_date.strftime('%B %d, %Y %H:%M:%S')}" if page.stats and page.stats.published_date else None
            )
            f_out_activated_date: Optional[str] = (
                f"│         ├─── Activated Date: {page.stats.activated_date.strftime('%B %d, %Y %H:%M:%S')}" if page.stats and page.stats.activated_date else None
            )
            f_out_edited_date: Optional[str] = (
                f"│        ├────── Edited Date: {page.stats.edited_date.strftime('%B %d, %Y %H:%M:%S')}" if page.stats and page.stats.edited_date else None
            )
            f_out_metadata_version: Optional[str] = f"│        ├─ Metadata Version: {page.stats.metadata_version}" if page.stats else None
            f_out_view_count: Optional[str] = f"│        ├─────── View Count: {page.stats.views}" if page.stats else None
            f_stats: list[str] = [
                stat
                for stat in [
                    f_out_modify_code_set,
                    f_out_published_date,
                    f_out_activated_date,
                    f_out_edited_date,
                    f_out_metadata_version,
                    f_out_view_count,
                ]
                if stat is not None
            ]

            if f_stats:
                f_stats[-1] = "└".join(f_stats[-1].split("├", 1))
            if f_out_stats:
                f_out_stats += "\n" + "\n".join(f_stats)

            f_fetched_values: list[str] = [
                value
                for value in [
                    f_out_page_id,
                    f_out_edit_code,
                    f_out_modify_code,
                    f_out_stats,
                    f_out_metadata,
                    f_out_markdown,
                ]
                if value is not None
            ]
            f_fetched_values[-1] = "└".join(f_fetched_values[-1].split("├", 1))
            output: str = f"\n{page.page_url} has the following data:\n" + "\n".join(f_fetched_values) + "\n"
            print(output)
        elif command == "exists":
            if not page_id:
                print("You must provide a page ID with the --page-id argument.")
                return
            elif edit_code or auth_token or new_page_id or new_edit_code or new_modify_code or markdown or metadata or overwrite:
                print('More arguments than expected for the "exists" command. Use "rentry help" for more information.')

            exists: bool = client.exists(page_id)
            print(exists)
        elif command == "create":
            if not markdown:
                print("You must provide markdown with the --markdown argument.")
                return
            elif auth_token or new_page_id or new_edit_code or new_modify_code or overwrite:
                print('More arguments than expected for the "create" command. Use "rentry help" for more information.')
                return

            page: RentrySyncPage = client.create(markdown, page_id, edit_code, metadata)
            print(f" Page URL: {page.page_url}\nEdit Code: {page.edit_code}\n Markdown: \n\n{page.markdown}")
        elif command == "delete":
            if not page_id or not edit_code:
                print("You must provide a page ID with the --page-id argument and an edit code with the --edit-code argument.")
                return
            elif auth_token or new_page_id or new_edit_code or new_modify_code or markdown or metadata or overwrite:
                print('More arguments than expected for the "delete" command. Use "rentry help" for more information.')
                return

            page: RentrySyncPage = client.delete(page_id, edit_code)
            print(f"{page.page_url} has been deleted.")
        elif command == "update":
            if not page_id or not edit_code:
                print("You must provide a page ID with the --page-id argument and an edit or modify code with the --edit-code argument.")
                return
            elif auth_token:
                print('More arguments than expected for the "update" command. Use "rentry help" for more information.')
                return

            is_modify_code: bool = edit_code.lower().startswith("m:")

            if is_modify_code and (new_page_id or new_edit_code or new_modify_code):
                print("Modify codes can't update the page ID, edit code, or modify code.")
                return

            passed_values: list[str] = [arg for arg in [new_page_id, new_edit_code, new_modify_code, markdown, metadata] if arg is not None]

            if not passed_values:
                print(f"{base_url}/{page_id} has not been updated due to no values being provided.")
                return

            page: RentrySyncPage = client.update(page_id, edit_code, new_page_id, new_edit_code, new_modify_code, markdown, metadata, overwrite)
            u_out_new_page_id: Optional[str] = f"├───── Page ID: {page.page_id}" if new_page_id else None
            u_out_new_edit_code: Optional[str] = f"├─── Edit Code: {page.edit_code}" if new_edit_code else None
            u_out_new_modify_code: Optional[str] = f"├─ Modify Code: {page.modify_code}" if new_modify_code else None
            u_out_metadata: Optional[str] = f"├──── Metadata: {page.metadata.encode()}" if bool(metadata) else None
            u_out_markdown: Optional[str] = f"├──── Markdown:─┐\n                ↓\n{page.markdown}" if page.markdown else "├──── Markdown: Cleared" if overwrite else None
            u_modified_values: list[str] = [
                value
                for value in [
                    u_out_new_page_id,
                    u_out_new_edit_code,
                    u_out_new_modify_code,
                    u_out_metadata,
                    u_out_markdown,
                ]
                if value is not None
            ]

            u_modified_values[-1] = "└".join(u_modified_values[-1].split("├", 1))
            output: str = f"\n{page.page_url} has been updated with the following values:\n" + "\n".join(u_modified_values) + "\n"
            print(output)
        else:
            print('Invalid command. Use "rentry help" for more information.')
    except (
        RentryExistingPageError,
        RentryInvalidAuthTokenError,
        RentryInvalidContentLengthError,
        RentryInvalidCSRFError,
        RentryInvalidEditCodeError,
        RentryInvalidMetadataError,
        RentryInvalidPageURLError,
        RentryInvalidResponseError,
        RentryNonExistentPageError,
    ) as e:
        print(str(e).replace("auth_token", "--auth-token"))
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()

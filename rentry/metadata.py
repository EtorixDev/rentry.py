from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Optional

from rentry.data import (
    ANY_URL_REGEX,
    CSS_COLOR_NAMES,
    CSS_SIZE_REGEX,
    EMAIL_REGEX,
    HEX_REGEX,
    RENTRY_PAGE_URL_REGEX,
    RGBA_REGEX,
    SECRET_REGEX,
)
from rentry.errors import RentryInvalidMetadataError


@dataclass(frozen=True)
class RentryPageStats:
    """---
    Represents the statistics for a Rentry page.

    #### Attributes
    - modify_code_set: `Optional[bool]` — Whether the modify code is set.
    - published_date: `Optional[datetime]` — The date the page was originally published.
    - activated_date: `Optional[datetime]` — The date the page was most recently re-activated.
    - edited_date: `Optional[datetime]` — The date the page was most recently edited.
    - metadata_version: `Optional[str]` — The version of the metadata.
    - views: `Optional[int]` — The number of views the page has received.
    """

    modify_code_set: Optional[bool] = None
    published_date: Optional[datetime] = None
    activated_date: Optional[datetime] = None
    edited_date: Optional[datetime] = None
    metadata_version: Optional[str] = None
    views: Optional[int] = None


class RentryPageMetadata:
    """---
    Represents the custom metadata for a Rentry page.

    #### Attributes
    - PAGE_TITLE: `Optional[str]` — The title of the page. Displayed in the browser tab.
        - Must be 60 characters or less.
    - PAGE_DESCRIPTION: `Optional[str]` — The description of the page. Displayed in search engine results and content snippets.
        - Must be 160 characters or less.
    - PAGE_IMAGE: `Optional[str]` — The cover image for the page. Displayed in search engine results and content snippets.
        - Must be a valid URL that is 1,000 characters or less.
    - PAGE_ICON: `Optional[str]` — The icon of the page. Displayed in the browser tab.
        - Must be a valid URL that is 1,000 characters or less.
    - SHARE_TITLE: `Optional[str]` — The title of the page when shared on social media.
        - Must be 60 characters or less.
    - SHARE_DESCRIPTION: `Optional[str]` — The description of the page when shared on social media.
        - Must be 160 characters or less.
    - SHARE_IMAGE: `Optional[str]` — The image of the page when shared on social media.
        - Must be a valid URL that is 1,000 characters or less.
    - SHARE_TWITTER_TITLE: `Optional[str]` — The title of the page when shared on Twitter.
        - Must be 60 characters or less.
    - SHARE_TWITTER_DESCRIPTION: `Optional[str]` — The description of the page when shared on Twitter.
        - Must be 160 characters or less.
    - SHARE_TWITTER_IMAGE: `Optional[str]` — The image of the page when shared on Twitter.
        - Must be a valid URL that is 1,000 characters or less.
    - OPTION_DISABLE_VIEWS: `Optional[bool]` — Disable the view counter and hide it from the page.
    - OPTION_DISABLE_SEARCH_ENGINE: `Optional[bool]` — Request search engines to not index the page.
    - OPTION_USE_ORIGINAL_PUB_DATE: `Optional[bool]` — If the page was deleted and recreated, use the original publication date.
    - ACCESS_RECOMMENDED_THEME: `Optional[Literal["dark", "light"]]` — Default theme for the page.
        - Must be "dark" or "light" if set.
    - ACCESS_EASY_READ: `Optional[str]` — The easy read URL for the page.
        - Must be a valid rentry URL that is 300 characters or less.
    - SECRET_VERIFY: `Optional[str]` — One or more external services to recover the page if you lose access.
        - Must be 3000 characters or less.
    - SECRET_RAW_ACCESS_CODE: `Optional[str]` — A code which allows access to the `/raw` version of the page.
        - Must be a code provided by rentry support that is 100 characters or less.
    - SECRET_EMAIL_ADDRESS: `Optional[str]` — The email address to recover the page if you lose access.
        - Must be a valid email address that is 300 characters or less.
    - CONTAINER_PADDING: `Optional[list[str]]` — The internal spacing between the main container and the content.
        - The total length of all values, including conjoining spaces, must be 64 characters or less.
        - Up to 4 values can be provided.
            - 1 value applies to all sides.
            - 2 values apply to top and bottom | left and right.
            - 3 values apply to top | left and right | bottom.
            - 4 values apply to top | right | bottom | left.
        - Must be a number followed by a supported format.
            - unitless: 0 - 40, no decimals.
            - px: 0 - 40, no decimals.
            - %: 0 - 25, up to 3 decimals.
            - vh: 0 - 15, up to 4 decimals.
            - hw: 0 - 20, up to 4 decimals.
            - rem: 0 - 7, up to 4 decimals.
    - CONTAINER_MAX_WIDTH: `Optional[str]` — Limits and centers the content container's width.
        - The length of the value must be 16 characters or less.
        - Must be a number followed by a supported format.
            - unitless: 100 - 1600, no decimals.
            - px: 100 - 1600, no decimals.
            - %: 10 - 100, up to 3 decimals.
            - vh: 10 - 100, up to 4 decimals.
            - hw: 10 - 100, up to 4 decimals.
            - rem: 3 - 25, up to 4 decimals.
    - CONTAINER_INNER_FOREGROUND_COLOR: `Optional[list[str]]` — The color of the inner foreground.
        - Overlays the content, so a semi-transparent color is recommended as a non-transparent color will hide the content.
        - Must be a valid HEX code, RGBA, or CSS color name.
        - The total length of all values, including conjoining spaces, must be 32 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to both light and dark mode.
            - 2 values apply to light and dark mode, respectively.
    - CONTAINER_INNER_BACKGROUND_COLOR: `Optional[list[str]]` — The color of the inner background.
        - Recommended to set a high contrast with the text color so the page is readable.
        - Set to transparent if you want to use a background image.
        - Must be a valid HEX code, RGBA, or CSS color name.
        - The total length of all values, including conjoining spaces, must be 32 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to both light and dark mode.
            - 2 values apply to light and dark mode, respectively.
    - CONTAINER_INNER_BACKGROUND_IMAGE: `Optional[str]` — The image of the inner background.
        - Must be a valid URL that is 1000 characters or less.
    - CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT: `Optional[Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]]` — The repeat style of the inner background image.
        - Must be "no-repeat", "repeat-x", "repeat-y", "round", or "space".
    - CONTAINER_INNER_BACKGROUND_IMAGE_POSITION: `Optional[Literal["center", "left", "right", "top", "bottom"]]` — The position of the inner background image.
        - Must be "center", "left", "right", "top", or "bottom".
    - CONTAINER_INNER_BACKGROUND_IMAGE_SIZE: `Optional[Literal["contain", "cover"] | str]` — The size of the inner background image.
        - The length of the value must be 16 characters or less.
        - Must be "contain", "cover", or a number followed by a supported format.
            - unitless: 1 - 3000, no decimals.
            - px: 1 - 3000, no decimals.
            - %: 0.1 - 150, up to 3 decimals.
            - vh: 0.1 - 200, up to 4 decimals.
            - hw: 0.1 - 200, up to 4 decimals.
            - rem: 0.1 - 50, up to 4 decimals.
    - CONTAINER_OUTER_FOREGROUND_COLOR: `Optional[list[str]]` — The color of the outer foreground.
        - Overlays the outer container, so a semi-transparent color is recommended if you want to see anything inside it.
        - Must be a valid HEX code, RGBA, or CSS color name.
        - The total length of all values, including conjoining spaces, must be 32 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to both light and dark mode.
            - 2 values apply to light and dark mode, respectively.
    - CONTAINER_OUTER_BACKGROUND_COLOR: `Optional[list[str]]` — The color of the outer background.
        - Everything else appears in front of this color.
        - Must be a valid HEX code, RGBA, or CSS color name.
        - The total length of all values, including conjoining spaces, must be 32 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to both light and dark mode.
            - 2 values apply to light and dark mode, respectively.
    - CONTAINER_OUTER_BACKGROUND_IMAGE: `Optional[str]` — The image of the outer background.
        - This will be in front of the outer background color and under the inner background color.
        - Must be a valid URL that is 1000 characters or less.
    - CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT: `Optional[Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]]` — The repeat style of the outer background image.
        - Must be "no-repeat", "repeat-x", "repeat-y", "round", or "space".
    - CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION: `Optional[Literal["center", "left", "right", "top", "bottom"]]` — The position of the outer background image.
        - Must be "center", "left", "right", "top", or "bottom".
    - CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE: `Optional[str]` — The size of the outer background image.
        - The length of the value must be 16 characters or less.
        - Must be "contain", "cover", or a number followed by a supported format.
            - unitless: 1 - 3000, no decimals.
            - px: 1 - 3000, no decimals.
            - %: 0.1 - 150, up to 3 decimals.
            - vh: 0.1 - 200, up to 4 decimals.
            - hw: 0.1 - 200, up to 4 decimals.
            - rem: 0.1 - 50, up to 4 decimals.
    - CONTAINER_BORDER_IMAGE: `Optional[str]` — The image of the container border.
        - Must be a valid URL that is 1,000 characters or less.
    - CONTAINER_BORDER_IMAGE_SLICE: `Optional[list[str]]` — Controls how the border image is cut up and displayed.
        - Must have `CONTAINER_BORDER_IMAGE` and `CONTAINER_BORDER_IMAGE_WIDTH` set.
        - The total length of all values, including conjoining spaces, must be 64 characters or less.
        - Up to 4 values can be provided.
            - 1 value applies to all sides.
            - 2 values apply to top and bottom | left and right.
            - 3 values apply to top | left and right | bottom.
            - 4 values apply to top | right | bottom | left.
        - Must be "fill" or a number followed by a supported format.
            - unitless: 0 - 20, no decimals.
            - %: 0 - 100, up to 3 decimals.
    - CONTAINER_BORDER_IMAGE_WIDTH: `Optional[list[str]]` — The width of the container border image.
        - Must have `CONTAINER_BORDER_IMAGE` set.
        - The total length of all values, including conjoining spaces, must be 64 characters or less.
        - Up to 4 values can be provided.
            - 1 value applies to all sides.
            - 2 values apply to top and bottom | left and right.
            - 3 values apply to top | left and right | bottom.
            - 4 values apply to top | right | bottom | left.
        - Must be "auto" or a number followed by a supported format.
            - unitless: 0 - 20, no decimals.
            - px: 0 - 30, no decimals.
            - %: 0 - 100, up to 3 decimals.
    - CONTAINER_BORDER_IMAGE_OUTSET: `Optional[list[str]]` — Controls where the border image appears in relation to the edges of the container.
        - Higher values push the border image further away from the container.
        - Must have `CONTAINER_BORDER_IMAGE` and `CONTAINER_BORDER_IMAGE_WIDTH` set.
        - The total length of all values, including conjoining spaces, must be 64 characters or less.
        - Up to 4 values can be provided.
            - 1 value applies to all sides.
            - 2 values apply to top and bottom | left and right.
            - 3 values apply to top | left and right | bottom.
            - 4 values apply to top | right | bottom | left.
        - Must be "auto" or a number followed by a supported format.
            - unitless: 0 - 20, no decimals.
            - px: 0 - 30, no decimals.
    - CONTAINER_BORDER_IMAGE_REPEAT: `Optional[list[str]]` — Controls how the border image is repeated.
        - Must have `CONTAINER_BORDER_IMAGE` and `CONTAINER_BORDER_IMAGE_WIDTH` set.
        - The total length of all values, including conjoining spaces, must be 32 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to all sides.
            - 2 values apply to top, middle, and bottom | left and right.
        - Must be "stretch", "repeat", "round", or "space".
    - CONTAINER_BORDER_COLOR: `Optional[list[str]]` — The color of the container border.
        - Must have `CONTAINER_BORDER_WIDTH` and `CONTAINER_BORDER_STYLE` set.
        - Must be a valid HEX code, RGBA, or CSS color name.
        - The total length of all values, including conjoining spaces, must be 120 characters or less.
        - Up to 4 values can be provided.
            - 1 value applies to all sides.
            - 2 values apply to top and bottom | left and right.
            - 3 values apply to top | left and right | bottom.
            - 4 values apply to top | right | bottom | left.
    - CONTAINER_BORDER_WIDTH: `Optional[list[str]]` — The width of the container border.
        - Must have `CONTAINER_BORDER_STYLE` set.
        - The total length of all values, including conjoining spaces, must be 64 characters or less.
        - Up to 4 values can be provided.
            - 1 value applies to all sides.
            - 2 values apply to top and bottom | left and right.
            - 3 values apply to top | left and right | bottom.
            - 4 values apply to top | right | bottom | left.
        - Must be a number followed by a supported format.
            - unitless: 0 - 30, no decimals.
            - px: 0 - 30, no decimals.
            - %: 0 - 100, up to 3 decimals.
            - vh: 0 - 100, up to 4 decimals.
            - hw: 0 - 100, up to 4 decimals.
            - rem: 0 - 10, up to 4 decimals.
    - CONTAINER_BORDER_STYLE: `Optional[list[Literal["dotted", "dashed", "solid", "double", "groove", "ridge", "inset", "outset"]]]` — The style of the container border.
        - Must have `CONTAINER_BORDER_WIDTH` set.
        - The total length of all values, including conjoining spaces, must be 64 characters or less.
        - Up to 4 values can be provided.
            - 1 value applies to all sides.
            - 2 values apply to top and bottom | left and right.
            - 3 values apply to top | left and right | bottom.
            - 4 values apply to top | right | bottom | left.
        - Must be "dotted", "dashed", "solid", "double", "groove", "ridge", "inset", or "outset".
    - CONTAINER_BORDER_RADIUS: `Optional[list[str]]` — The radius of the container border.
        - The total length of all values, including conjoining spaces, must be 64 characters or less.
        - Up to 4 values can be provided.
            - 1 value applies to all corners.
            - 2 values apply to top-left and bottom-right | top-right and bottom-left.
            - 3 values apply to top-left | top-right and bottom-left | bottom-right.
            - 4 values apply to top-left | top-right | bottom-right | bottom-left.
        - Must be a number followed by a supported format.
            - unitless: 0 - 200, no decimals.
            - px: 0 - 200, no decimals.
            - %: 0 - 50, up to 3 decimals.
            - vh: 0 - 40, up to 4 decimals.
            - hw: 0 - 40, up to 4 decimals.
            - rem: 0 - 30, up to 4 decimals.
    - CONTAINER_SHADOW_COLOR: `Optional[str]` — The color of the container shadow.
        - Must have `CONTAINER_SHADOW_OFFSET`, `CONTAINER_SHADOW_SPREAD`, or `CONTAINER_SHADOW_BLUR` set.
        - Must be a valid HEX code, RGBA, or CSS color name.
        - The total length of the value must be 32 characters or less.
    - CONTAINER_SHADOW_OFFSET: `Optional[list[str]]` — The offset of the container shadow.
        - Must have `CONTAINER_SHADOW_COLOR` set.
        - The total length of all values, including conjoining spaces, must be 32 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to both horizontal and vertical offset.
            - 2 values apply to horizontal and vertical offset, respectively.
        - Must be a number followed by a supported format.
            - unitless: -15 - 15, no decimals.
            - px: -15 - 15, no decimals.
            - %: -5 - 5, up to 3 decimals.
            - vh: -2 - 2, up to 4 decimals.
            - hw: -2 - 2, up to 4 decimals.
            - rem: -4 - 2, up to 4 decimals.
    - CONTAINER_SHADOW_SPREAD: `Optional[str]` — The spread of the container shadow.
        - Must have `CONTAINER_SHADOW_COLOR` set.
        - The total length of the value must be 12 characters or less.
        - Must be a number followed by a supported format.
            - unitless: 0 - 30, no decimals.
            - px: 0 - 30, no decimals.
            - %: 0 - 10, up to 3 decimals.
            - vh: 0 - 5, up to 4 decimals.
            - hw: 0 - 5, up to 4 decimals.
            - rem: 0 - 3, up to 4 decimals.
    - CONTAINER_SHADOW_BLUR: `Optional[str]` — The blur of the container shadow.
        - Must have `CONTAINER_SHADOW_COLOR` set.
        - The total length of the value must be 12 characters or less.
        - Must be a number followed by a supported format.
            - unitless: 0 - 30, no decimals.
            - px: 0 - 30, no decimals.
            - %: 0 - 10, up to 3 decimals.
            - vh: 0 - 5, up to 4 decimals.
            - hw: 0 - 5, up to 4 decimals.
            - rem: 0 - 3, up to 4 decimals.
    - CONTENT_FONT: `Optional[list[str]]` — The font of the content.
        - Must be a valid font name listed on Google Fonts with spaces replaced by underscores.
        - Invalid fonts will be ignored by the rentry API.
        - The total length of all values, including conjoining spaces, must be 1,000 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to all page content.
            - 2 values apply to page content and headings, respectively.
    - CONTENT_FONT_WEIGHT: `Optional[list[Literal["bold", "bolder", "lighter", "normal", "100", "200", "300", "400", "500", "600", "700", "800", "900"]]]` — The boldness of the content font.
        - The total length of all values, including conjoining spaces, must be 24 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to all page content.
            - 2 values apply to page content and headings, respectively.
        - Must be "bold", "bolder", "lighter", "normal", "100", "200", "300", "400", "500", "600", "700", "800", or "900".
    - CONTENT_TEXT_DIRECTION: `Optional[Literal["ltr", "rtl"]]` — The direction of the content text.
        - Must be "ltr" or "rtl".
    - CONTENT_TEXT_SIZE: `Optional[list[str]]` — The size of the content text.
        - Default value is "16px 1rem 2.5rem 2rem 1.75rem 1.5rem 1.25rem 1rem 1rem 1rem 1rem 14px".
        - The total length of all values, including conjoining spaces, must be 128 characters or less.
        - Up to 12 values can be provided.
            - The first value applies to all page content and is the base for any relative values for the other 11.
            - The second value applies to paragraphs.
            - The third value applies to Heading 1.
            - The fourth value applies to Heading 2.
            - The fifth value applies to Heading 3.
            - The sixth value applies to Heading 4.
            - The seventh value applies to Heading 5.
            - The eighth value applies to Heading 6.
            - The ninth value applies to list items.
            - The tenth value applies to links.
            - The eleventh value applies to quotes.
            - The twelfth value applies to code.
        - Must be a number followed by a supported format.
            - unitless: 8 - 64, no decimals.
            - px: 8 - 64, no decimals.
            - %: 10 - 500, up to 3 decimals.
            - vh: 2 - 10, up to 4 decimals.
            - hw: 2 - 10, up to 4 decimals.
            - rem: 0.3 - 8, up to 4 decimals.
    - CONTENT_TEXT_ALIGN: `Optional[Literal["right", "center", "justify"]]` — The alignment of the content text.
        - Must be "right", "center", or "justify".
    - CONTENT_TEXT_SHADOW_COLOR: `Optional[str]` — The color of the content text shadow.
        - Must have `CONTENT_TEXT_SHADOW_OFFSET` set.
        - Must be a valid HEX code, RGBA, or CSS color name.
        - The total length of the value must be 32 characters or less.
    - CONTENT_TEXT_SHADOW_OFFSET: `Optional[list[str]]` — The offset of the content text shadow.
        - Must have `CONTENT_TEXT_SHADOW_COLOR` set.
        - The total length of all values, including conjoining spaces, must be 32 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to both horizontal and vertical offset.
            - 2 values apply to horizontal and vertical offset, respectively.
        - Must be a number followed by a supported format.
            - unitless: -15 - 15, no decimals.
            - px: -15 - 15, no decimals.
            - %: -5 - 5, up to 3 decimals.
            - vh: -2 - 2, up to 4 decimals.
            - hw: -2 - 2, up to 4 decimals.
            - rem: -2 - 2, up to 4 decimals.
    - CONTENT_TEXT_SHADOW_BLUR: `Optional[str]` — The blur of the content text shadow.
        - Must have `CONTENT_TEXT_SHADOW_COLOR` and `CONTENT_TEXT_SHADOW_OFFSET` set.
        - The total length of the value must be 12 characters or less.
        - Must be a number followed by a supported format.
            - unitless: 0 - 30, no decimals.
            - px: 0 - 30, no decimals.
            - %: 0 - 10, up to 3 decimals.
            - vh: 0 - 5, up to 4 decimals.
            - hw: 0 - 5, up to 4 decimals.
            - rem: 0 - 3, up to 4 decimals.
    - CONTENT_TEXT_COLOR: `Optional[list[str]]` — The base color for page text. Inline colors will override this.
        - The total length of all values, including conjoining spaces, must be 128 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to both light and dark mode.
            - 2 values apply to light and dark mode, respectively.
        - Must be a valid HEX code, RGBA, or CSS color name.
    - CONTENT_LINK_COLOR: `Optional[list[str]]` — The color of links in the content.
        - The total length of all values, including conjoining spaces, must be 16 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to both light and dark mode.
            - 2 values apply to light and dark mode, respectively.
        - Must be a valid HEX code, RGBA, or CSS color name.
    - CONTENT_BULLET_COLOR: `Optional[list[str]]` — The color of bullet points in the content.
        - The total length of all values, including conjoining spaces, must be 64 characters or less.
        - Up to 2 values can be provided.
            - 1 value applies to both light and dark mode.
            - 2 values apply to light and dark mode, respectively.
        - Must be a valid HEX code, RGBA, or CSS color name.
    - CONTENT_LINK_BEHAVIOR: `Optional[list[Literal["same", "new"]]]` — The behavior of links in the content.
        - Up to 2 values can be provided.
            - 1 value applies to all links.
            - 2 values apply to internal and external links, respectively.
        - Must be "same" or "new".
    - SAFETY_PAGE_WARNING: `Optional[list[Literal["adult", "sensitive", "epilepsy", "custom"]]]` — Adds a warning popup to your page before allowing visitors to view.
        - The total length of all values, including conjoining spaces, must be 100 characters or less.
        - Up to 4 values can be provided.
        - Must be "adult", "sensitive", "epilepsy", or "custom".
    - SAFETY_PAGE_WARNING_DESCRIPTION: `Optional[str]` — Provide your own text to the warning popup created by SAFETY_PAGE_WARNING.
        - Must be 240 characters or less.
    - SAFETY_MEDIA_BLUR: `Optional[bool]` — Blurs all images in your page and requires them to be clicked before showing.
        - Allows you to display sensitive images that some viewers may prefer not to see.
    - SAFETY_LINK_WARNING: `Optional[list[Literal["adult", "epilepsy", "sensitive"]]]` — Triggers a popup when clicking on a link within your content.
        - The total length of all values, including conjoining spaces, must be 100 characters or less.
        - Up to 3 values can be provided.
        - Must be "adult", "epilepsy", or "sensitive".
    - SAFETY_LINK_WARNING_DESCRIPTION: `Optional[str]` — Provide your own text to the link warning popup.
        - Must be 240 characters or less.
    - SAFETY_PAGE_FLAG: `Optional[list[Literal["adult", "epilepsy", "sensitive"]]]` — Creates a visual icon on your page to inform readers that a page contains certain material.
        - Similar to SAFETY_PAGE_WARNING, except it does not trigger a popup.
        - The total length of all values, including conjoining spaces, must be 100 characters or less.
        - Up to 3 values can be provided.
        - Must be "adult", "epilepsy", or "sensitive".

    #### Methods
    - `validate()` — Validate all locally validatable metadata attributes.
        - If a non-existent rentry url is set for `ACCESS_EASY_READ`, the rentry API will reject the value.
        - If an invalid Google Font is set for `CONTENT_FONT`, the rentry API will silently ignore the value.
    - `encode()` — Encode the metadata to a JSON string for the rentry API.
    - `decode()` — Decode the metadata from the rentry API into this metadata object.
    - `build()` — Build a metadata object from a JSON string or dictionary.

    #### Raises
    - `RentryInvalidMetadataError` when one or more metadata attributes are invalid.
    """

    def __init__(
        self,
        PAGE_TITLE: Optional[str] = None,
        PAGE_DESCRIPTION: Optional[str] = None,
        PAGE_IMAGE: Optional[str] = None,
        PAGE_ICON: Optional[str] = None,
        SHARE_TITLE: Optional[str] = None,
        SHARE_DESCRIPTION: Optional[str] = None,
        SHARE_IMAGE: Optional[str] = None,
        SHARE_TWITTER_TITLE: Optional[str] = None,
        SHARE_TWITTER_DESCRIPTION: Optional[str] = None,
        SHARE_TWITTER_IMAGE: Optional[str] = None,
        OPTION_DISABLE_VIEWS: Optional[bool] = None,
        OPTION_DISABLE_SEARCH_ENGINE: Optional[bool] = None,
        OPTION_USE_ORIGINAL_PUB_DATE: Optional[bool] = None,
        ACCESS_RECOMMENDED_THEME: Optional[str] = None,
        ACCESS_EASY_READ: Optional[str] = None,
        SECRET_VERIFY: Optional[str] = None,
        SECRET_RAW_ACCESS_CODE: Optional[str] = None,
        SECRET_EMAIL_ADDRESS: Optional[str] = None,
        CONTAINER_PADDING: Optional[list[str]] = None,
        CONTAINER_MAX_WIDTH: Optional[str] = None,
        CONTAINER_INNER_FOREGROUND_COLOR: Optional[list[str]] = None,
        CONTAINER_INNER_BACKGROUND_COLOR: Optional[list[str]] = None,
        CONTAINER_INNER_BACKGROUND_IMAGE: Optional[str] = None,
        CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT: Optional[Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]] = None,
        CONTAINER_INNER_BACKGROUND_IMAGE_POSITION: Optional[Literal["center", "left", "right", "top", "bottom"]] = None,
        CONTAINER_INNER_BACKGROUND_IMAGE_SIZE: Optional[Literal["contain", "cover"] | str] = None,
        CONTAINER_OUTER_FOREGROUND_COLOR: Optional[list[str]] = None,
        CONTAINER_OUTER_BACKGROUND_COLOR: Optional[list[str]] = None,
        CONTAINER_OUTER_BACKGROUND_IMAGE: Optional[str] = None,
        CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT: Optional[Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]] = None,
        CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION: Optional[Literal["center", "left", "right", "top", "bottom"]] = None,
        CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE: Optional[str] = None,
        CONTAINER_BORDER_IMAGE: Optional[str] = None,
        CONTAINER_BORDER_IMAGE_SLICE: Optional[list[str]] = None,
        CONTAINER_BORDER_IMAGE_WIDTH: Optional[list[str]] = None,
        CONTAINER_BORDER_IMAGE_OUTSET: Optional[list[str]] = None,
        CONTAINER_BORDER_IMAGE_REPEAT: Optional[list[str]] = None,
        CONTAINER_BORDER_COLOR: Optional[list[str]] = None,
        CONTAINER_BORDER_WIDTH: Optional[list[str]] = None,
        CONTAINER_BORDER_STYLE: Optional[list[Literal["dotted", "dashed", "solid", "double", "groove", "ridge", "inset", "outset"]]] = None,
        CONTAINER_BORDER_RADIUS: Optional[list[str]] = None,
        CONTAINER_SHADOW_COLOR: Optional[str] = None,
        CONTAINER_SHADOW_OFFSET: Optional[list[str]] = None,
        CONTAINER_SHADOW_SPREAD: Optional[str] = None,
        CONTAINER_SHADOW_BLUR: Optional[str] = None,
        CONTENT_FONT: Optional[list[str]] = None,
        CONTENT_FONT_WEIGHT: Optional[list[Literal["bold", "bolder", "lighter", "normal", "100", "200", "300", "400", "500", "600", "700", "800", "900"]]] = None,
        CONTENT_TEXT_DIRECTION: Optional[Literal["ltr", "rtl"]] = None,
        CONTENT_TEXT_SIZE: Optional[list[str]] = None,
        CONTENT_TEXT_ALIGN: Optional[Literal["right", "center", "justify"]] = None,
        CONTENT_TEXT_SHADOW_COLOR: Optional[str] = None,
        CONTENT_TEXT_SHADOW_OFFSET: Optional[list[str]] = None,
        CONTENT_TEXT_SHADOW_BLUR: Optional[str] = None,
        CONTENT_TEXT_COLOR: Optional[list[str]] = None,
        CONTENT_LINK_COLOR: Optional[list[str]] = None,
        CONTENT_BULLET_COLOR: Optional[list[str]] = None,
        CONTENT_LINK_BEHAVIOR: Optional[list[Literal["same", "new"]]] = None,
        SAFETY_PAGE_WARNING: Optional[list[Literal["adult", "sensitive", "epilepsy", "custom"]]] = None,
        SAFETY_PAGE_WARNING_DESCRIPTION: Optional[str] = None,
        SAFETY_MEDIA_BLUR: Optional[bool] = None,
        SAFETY_LINK_WARNING: Optional[list[Literal["adult", "epilepsy", "sensitive"]]] = None,
        SAFETY_LINK_WARNING_DESCRIPTION: Optional[str] = None,
        SAFETY_PAGE_FLAG: Optional[list[Literal["adult", "epilepsy", "sensitive"]]] = None,
    ) -> None:
        self._PAGE_TITLE: Optional[str] = PAGE_TITLE.strip() if PAGE_TITLE and PAGE_TITLE.strip() else None
        self._PAGE_DESCRIPTION: Optional[str] = PAGE_DESCRIPTION.strip() if PAGE_DESCRIPTION and PAGE_DESCRIPTION.strip() else None
        self._PAGE_IMAGE: Optional[str] = PAGE_IMAGE.strip() if PAGE_IMAGE and PAGE_IMAGE.strip() else None
        self._PAGE_ICON: Optional[str] = PAGE_ICON.strip() if PAGE_ICON and PAGE_ICON.strip() else None
        self._SHARE_TITLE: Optional[str] = SHARE_TITLE.strip() if SHARE_TITLE and SHARE_TITLE.strip() else None
        self._SHARE_DESCRIPTION: Optional[str] = SHARE_DESCRIPTION.strip() if SHARE_DESCRIPTION and SHARE_DESCRIPTION.strip() else None
        self._SHARE_IMAGE: Optional[str] = SHARE_IMAGE.strip() if SHARE_IMAGE and SHARE_IMAGE.strip() else None
        self._SHARE_TWITTER_TITLE: Optional[str] = SHARE_TWITTER_TITLE.strip() if SHARE_TWITTER_TITLE and SHARE_TWITTER_TITLE.strip() else None
        self._SHARE_TWITTER_DESCRIPTION: Optional[str] = SHARE_TWITTER_DESCRIPTION.strip() if SHARE_TWITTER_DESCRIPTION and SHARE_TWITTER_DESCRIPTION.strip() else None
        self._SHARE_TWITTER_IMAGE: Optional[str] = SHARE_TWITTER_IMAGE.strip() if SHARE_TWITTER_IMAGE and SHARE_TWITTER_IMAGE.strip() else None
        self._OPTION_DISABLE_VIEWS: Optional[bool] = OPTION_DISABLE_VIEWS
        self._OPTION_DISABLE_SEARCH_ENGINE: Optional[bool] = OPTION_DISABLE_SEARCH_ENGINE
        self._OPTION_USE_ORIGINAL_PUB_DATE: Optional[bool] = OPTION_USE_ORIGINAL_PUB_DATE
        self._ACCESS_RECOMMENDED_THEME: Optional[str] = ACCESS_RECOMMENDED_THEME.strip() if ACCESS_RECOMMENDED_THEME and ACCESS_RECOMMENDED_THEME.strip() else None
        self._ACCESS_EASY_READ: Optional[str] = ("/" + ACCESS_EASY_READ.strip().split("/")[-1]) if ACCESS_EASY_READ and ACCESS_EASY_READ.strip() else None
        self._SECRET_VERIFY: Optional[str] = SECRET_VERIFY.strip() if SECRET_VERIFY and SECRET_VERIFY.strip() else None
        self._SECRET_RAW_ACCESS_CODE: Optional[str] = SECRET_RAW_ACCESS_CODE.strip() if SECRET_RAW_ACCESS_CODE and SECRET_RAW_ACCESS_CODE.strip() else None
        self._SECRET_EMAIL_ADDRESS: Optional[str] = SECRET_EMAIL_ADDRESS.strip() if SECRET_EMAIL_ADDRESS and SECRET_EMAIL_ADDRESS.strip() else None
        self._CONTAINER_PADDING: Optional[list[str]] = [val.strip() for val in CONTAINER_PADDING if val.strip()] if CONTAINER_PADDING else None
        self._CONTAINER_MAX_WIDTH: Optional[str] = CONTAINER_MAX_WIDTH.strip() if CONTAINER_MAX_WIDTH and CONTAINER_MAX_WIDTH.strip() else None
        if CONTAINER_INNER_FOREGROUND_COLOR:
            for index, item in enumerate(CONTAINER_INNER_FOREGROUND_COLOR):
                CONTAINER_INNER_FOREGROUND_COLOR[index] = item.replace(" ", "")
        self._CONTAINER_INNER_FOREGROUND_COLOR: Optional[list[str]] = [val for val in CONTAINER_INNER_FOREGROUND_COLOR if val] if CONTAINER_INNER_FOREGROUND_COLOR else None
        if CONTAINER_INNER_BACKGROUND_COLOR:
            for index, item in enumerate(CONTAINER_INNER_BACKGROUND_COLOR):
                CONTAINER_INNER_BACKGROUND_COLOR[index] = item.replace(" ", "")
        self._CONTAINER_INNER_BACKGROUND_COLOR: Optional[list[str]] = [val for val in CONTAINER_INNER_BACKGROUND_COLOR if val] if CONTAINER_INNER_BACKGROUND_COLOR else None
        self._CONTAINER_INNER_BACKGROUND_IMAGE: Optional[str] = (
            CONTAINER_INNER_BACKGROUND_IMAGE.strip() if CONTAINER_INNER_BACKGROUND_IMAGE and CONTAINER_INNER_BACKGROUND_IMAGE.strip() else None
        )
        self._CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT: Optional[Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]] = CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT
        self._CONTAINER_INNER_BACKGROUND_IMAGE_POSITION: Optional[Literal["center", "left", "right", "top", "bottom"]] = CONTAINER_INNER_BACKGROUND_IMAGE_POSITION
        self._CONTAINER_INNER_BACKGROUND_IMAGE_SIZE: Optional[Literal["contain", "cover"] | str] = CONTAINER_INNER_BACKGROUND_IMAGE_SIZE
        if CONTAINER_OUTER_FOREGROUND_COLOR:
            for index, item in enumerate(CONTAINER_OUTER_FOREGROUND_COLOR):
                CONTAINER_OUTER_FOREGROUND_COLOR[index] = item.replace(" ", "")
        self._CONTAINER_OUTER_FOREGROUND_COLOR: Optional[list[str]] = [val for val in CONTAINER_OUTER_FOREGROUND_COLOR if val] if CONTAINER_OUTER_FOREGROUND_COLOR else None
        if CONTAINER_OUTER_BACKGROUND_COLOR:
            for index, item in enumerate(CONTAINER_OUTER_BACKGROUND_COLOR):
                CONTAINER_OUTER_BACKGROUND_COLOR[index] = item.replace(" ", "")
        self._CONTAINER_OUTER_BACKGROUND_COLOR: Optional[list[str]] = [val for val in CONTAINER_OUTER_BACKGROUND_COLOR if val] if CONTAINER_OUTER_BACKGROUND_COLOR else None
        self._CONTAINER_OUTER_BACKGROUND_IMAGE: Optional[str] = (
            CONTAINER_OUTER_BACKGROUND_IMAGE.strip() if CONTAINER_OUTER_BACKGROUND_IMAGE and CONTAINER_OUTER_BACKGROUND_IMAGE.strip() else None
        )
        self._CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT: Optional[Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]] = CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT
        self._CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION: Optional[Literal["center", "left", "right", "top", "bottom"]] = CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION
        self._CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE: Optional[str] = (
            CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE.strip() if CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE and CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE.strip() else None
        )
        self._CONTAINER_BORDER_IMAGE: Optional[str] = CONTAINER_BORDER_IMAGE.strip() if CONTAINER_BORDER_IMAGE and CONTAINER_BORDER_IMAGE.strip() else None
        self._CONTAINER_BORDER_IMAGE_SLICE: Optional[list[str]] = [val.strip() for val in CONTAINER_BORDER_IMAGE_SLICE if val.strip()] if CONTAINER_BORDER_IMAGE_SLICE else None
        self._CONTAINER_BORDER_IMAGE_WIDTH: Optional[list[str]] = [val.strip() for val in CONTAINER_BORDER_IMAGE_WIDTH if val.strip()] if CONTAINER_BORDER_IMAGE_WIDTH else None
        self._CONTAINER_BORDER_IMAGE_OUTSET: Optional[list[str]] = [val.strip() for val in CONTAINER_BORDER_IMAGE_OUTSET if val.strip()] if CONTAINER_BORDER_IMAGE_OUTSET else None
        self._CONTAINER_BORDER_IMAGE_REPEAT: Optional[list[str]] = [val.strip() for val in CONTAINER_BORDER_IMAGE_REPEAT if val.strip()] if CONTAINER_BORDER_IMAGE_REPEAT else None
        if CONTAINER_BORDER_COLOR:
            for index, item in enumerate(CONTAINER_BORDER_COLOR):
                CONTAINER_BORDER_COLOR[index] = item.replace(" ", "")
        self._CONTAINER_BORDER_COLOR: Optional[list[str]] = [val for val in CONTAINER_BORDER_COLOR if val] if CONTAINER_BORDER_COLOR else None
        self._CONTAINER_BORDER_WIDTH: Optional[list[str]] = [val.strip() for val in CONTAINER_BORDER_WIDTH if val.strip()] if CONTAINER_BORDER_WIDTH else None
        self._CONTAINER_BORDER_STYLE: Optional[list[Literal["dotted", "dashed", "solid", "double", "groove", "ridge", "inset", "outset"]]] = CONTAINER_BORDER_STYLE
        self._CONTAINER_BORDER_RADIUS: Optional[list[str]] = [val.strip() for val in CONTAINER_BORDER_RADIUS if val.strip()] if CONTAINER_BORDER_RADIUS else None
        self._CONTAINER_SHADOW_COLOR: Optional[str] = CONTAINER_SHADOW_COLOR.replace(" ", "") if CONTAINER_SHADOW_COLOR and CONTAINER_SHADOW_COLOR.replace(" ", "") else None
        self._CONTAINER_SHADOW_OFFSET: Optional[list[str]] = [val.strip() for val in CONTAINER_SHADOW_OFFSET if val.strip()] if CONTAINER_SHADOW_OFFSET else None
        self._CONTAINER_SHADOW_SPREAD: Optional[str] = CONTAINER_SHADOW_SPREAD.strip() if CONTAINER_SHADOW_SPREAD and CONTAINER_SHADOW_SPREAD.strip() else None
        self._CONTAINER_SHADOW_BLUR: Optional[str] = CONTAINER_SHADOW_BLUR.strip() if CONTAINER_SHADOW_BLUR and CONTAINER_SHADOW_BLUR.strip() else None
        self._CONTENT_FONT: Optional[list[str]] = [val.strip() for val in CONTENT_FONT if val.strip()] if CONTENT_FONT else None
        self._CONTENT_FONT_WEIGHT: Optional[list[Literal["bold", "bolder", "lighter", "normal", "100", "200", "300", "400", "500", "600", "700", "800", "900"]]] = (
            CONTENT_FONT_WEIGHT
        )
        self._CONTENT_TEXT_DIRECTION: Optional[Literal["ltr", "rtl"]] = CONTENT_TEXT_DIRECTION
        self._CONTENT_TEXT_SIZE: Optional[list[str]] = [val.strip() for val in CONTENT_TEXT_SIZE if val.strip()] if CONTENT_TEXT_SIZE else None
        self._CONTENT_TEXT_ALIGN: Optional[Literal["right", "center", "justify"]] = CONTENT_TEXT_ALIGN
        self._CONTENT_TEXT_SHADOW_COLOR: Optional[str] = (
            CONTENT_TEXT_SHADOW_COLOR.replace(" ", "") if CONTENT_TEXT_SHADOW_COLOR and CONTENT_TEXT_SHADOW_COLOR.replace(" ", "") else None
        )
        self._CONTENT_TEXT_SHADOW_OFFSET: Optional[list[str]] = [val.strip() for val in CONTENT_TEXT_SHADOW_OFFSET if val.strip()] if CONTENT_TEXT_SHADOW_OFFSET else None
        self._CONTENT_TEXT_SHADOW_BLUR: Optional[str] = CONTENT_TEXT_SHADOW_BLUR.strip() if CONTENT_TEXT_SHADOW_BLUR and CONTENT_TEXT_SHADOW_BLUR.strip() else None
        if CONTENT_TEXT_COLOR:
            for index, item in enumerate(CONTENT_TEXT_COLOR):
                CONTENT_TEXT_COLOR[index] = item.replace(" ", "")
        self._CONTENT_TEXT_COLOR: Optional[list[str]] = [val for val in CONTENT_TEXT_COLOR if val] if CONTENT_TEXT_COLOR else None
        if CONTENT_LINK_COLOR:
            for index, item in enumerate(CONTENT_LINK_COLOR):
                CONTENT_LINK_COLOR[index] = item.replace(" ", "")
        self._CONTENT_LINK_COLOR: Optional[list[str]] = [val for val in CONTENT_LINK_COLOR if val] if CONTENT_LINK_COLOR else None
        if CONTENT_BULLET_COLOR:
            for index, item in enumerate(CONTENT_BULLET_COLOR):
                CONTENT_BULLET_COLOR[index] = item.replace(" ", "")
        self._CONTENT_BULLET_COLOR: Optional[list[str]] = [val for val in CONTENT_BULLET_COLOR if val] if CONTENT_BULLET_COLOR else None
        self._CONTENT_LINK_BEHAVIOR: Optional[list[Literal["same", "new"]]] = CONTENT_LINK_BEHAVIOR
        self._SAFETY_PAGE_WARNING: Optional[list[Literal["adult", "sensitive", "epilepsy", "custom"]]] = SAFETY_PAGE_WARNING
        self._SAFETY_PAGE_WARNING_DESCRIPTION: Optional[str] = SAFETY_PAGE_WARNING_DESCRIPTION.strip() if SAFETY_PAGE_WARNING_DESCRIPTION and SAFETY_PAGE_WARNING_DESCRIPTION.strip() else None
        self._SAFETY_MEDIA_BLUR: Optional[bool] = SAFETY_MEDIA_BLUR
        self._SAFETY_LINK_WARNING: Optional[list[Literal["adult", "epilepsy", "sensitive"]]] = SAFETY_LINK_WARNING
        self._SAFETY_LINK_WARNING_DESCRIPTION: Optional[str] = SAFETY_LINK_WARNING_DESCRIPTION.strip() if SAFETY_LINK_WARNING_DESCRIPTION and SAFETY_LINK_WARNING_DESCRIPTION.strip() else None
        self._SAFETY_PAGE_FLAG: Optional[list[Literal["adult", "epilepsy", "sensitive"]]] = SAFETY_PAGE_FLAG

        self.validate()

    @property
    def PAGE_TITLE(self) -> Optional[str]:
        """The title of the page. Displayed in the browser tab."""
        return self._PAGE_TITLE

    @PAGE_TITLE.setter
    def PAGE_TITLE(self, value: Optional[str]) -> None:
        self._PAGE_TITLE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def PAGE_DESCRIPTION(self) -> Optional[str]:
        """The description of the page. Displayed in search engine results and content snippets."""
        return self._PAGE_DESCRIPTION

    @PAGE_DESCRIPTION.setter
    def PAGE_DESCRIPTION(self, value: Optional[str]) -> None:
        self._PAGE_DESCRIPTION = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def PAGE_IMAGE(self) -> Optional[str]:
        """The cover image for the page. Displayed in search engine results and content snippets."""
        return self._PAGE_IMAGE

    @PAGE_IMAGE.setter
    def PAGE_IMAGE(self, value: Optional[str]) -> None:
        self._PAGE_IMAGE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def PAGE_ICON(self) -> Optional[str]:
        """The icon of the page. Displayed in the browser tab."""
        return self._PAGE_ICON

    @PAGE_ICON.setter
    def PAGE_ICON(self, value: Optional[str]) -> None:
        self._PAGE_ICON = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def SHARE_TITLE(self) -> Optional[str]:
        """The title of the page when shared on social media."""
        return self._SHARE_TITLE

    @SHARE_TITLE.setter
    def SHARE_TITLE(self, value: Optional[str]) -> None:
        self._SHARE_TITLE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def SHARE_DESCRIPTION(self) -> Optional[str]:
        """The description of the page when shared on social media."""
        return self._SHARE_DESCRIPTION

    @SHARE_DESCRIPTION.setter
    def SHARE_DESCRIPTION(self, value: Optional[str]) -> None:
        self._SHARE_DESCRIPTION = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def SHARE_IMAGE(self) -> Optional[str]:
        """The image of the page when shared on social media."""
        return self._SHARE_IMAGE

    @SHARE_IMAGE.setter
    def SHARE_IMAGE(self, value: Optional[str]) -> None:
        self._SHARE_IMAGE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def SHARE_TWITTER_TITLE(self) -> Optional[str]:
        """The title of the page when shared on Twitter."""
        return self._SHARE_TWITTER_TITLE

    @SHARE_TWITTER_TITLE.setter
    def SHARE_TWITTER_TITLE(self, value: Optional[str]) -> None:
        self._SHARE_TWITTER_TITLE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def SHARE_TWITTER_DESCRIPTION(self) -> Optional[str]:
        """The description of the page when shared on Twitter."""
        return self._SHARE_TWITTER_DESCRIPTION

    @SHARE_TWITTER_DESCRIPTION.setter
    def SHARE_TWITTER_DESCRIPTION(self, value: Optional[str]) -> None:
        self._SHARE_TWITTER_DESCRIPTION = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def SHARE_TWITTER_IMAGE(self) -> Optional[str]:
        """The image of the page when shared on Twitter."""
        return self._SHARE_TWITTER_IMAGE

    @SHARE_TWITTER_IMAGE.setter
    def SHARE_TWITTER_IMAGE(self, value: Optional[str]) -> None:
        self._SHARE_TWITTER_IMAGE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def OPTION_DISABLE_VIEWS(self) -> Optional[bool]:
        """Disable the view counter and hide it from the page."""
        return self._OPTION_DISABLE_VIEWS

    @OPTION_DISABLE_VIEWS.setter
    def OPTION_DISABLE_VIEWS(self, value: Optional[bool]) -> None:
        self._OPTION_DISABLE_VIEWS = value
        self.validate()

    @property
    def OPTION_DISABLE_SEARCH_ENGINE(self) -> Optional[bool]:
        """Request search engines to not index the page."""
        return self._OPTION_DISABLE_SEARCH_ENGINE

    @OPTION_DISABLE_SEARCH_ENGINE.setter
    def OPTION_DISABLE_SEARCH_ENGINE(self, value: Optional[bool]) -> None:
        self._OPTION_DISABLE_SEARCH_ENGINE = value
        self.validate()

    @property
    def OPTION_USE_ORIGINAL_PUB_DATE(self) -> Optional[bool]:
        """If the page was deleted and recreated, use the original publication date."""
        return self._OPTION_USE_ORIGINAL_PUB_DATE

    @OPTION_USE_ORIGINAL_PUB_DATE.setter
    def OPTION_USE_ORIGINAL_PUB_DATE(self, value: Optional[bool]) -> None:
        self._OPTION_USE_ORIGINAL_PUB_DATE = value
        self.validate()

    @property
    def ACCESS_RECOMMENDED_THEME(self) -> Optional[str]:
        """Default theme for the page."""
        return self._ACCESS_RECOMMENDED_THEME

    @ACCESS_RECOMMENDED_THEME.setter
    def ACCESS_RECOMMENDED_THEME(self, value: Optional[str]) -> None:
        self._ACCESS_RECOMMENDED_THEME = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def ACCESS_EASY_READ(self) -> Optional[str]:
        """The easy read URL for the page."""
        return self._ACCESS_EASY_READ

    @ACCESS_EASY_READ.setter
    def ACCESS_EASY_READ(self, value: Optional[str]) -> None:
        self._ACCESS_EASY_READ = ("/" + value.strip().split("/")[-1]) if value and value.strip() else None
        self.validate()

    @property
    def SECRET_VERIFY(self) -> Optional[str]:
        """One or more external services to recover the page if you lose access."""
        return self._SECRET_VERIFY

    @SECRET_VERIFY.setter
    def SECRET_VERIFY(self, value: Optional[str]) -> None:
        self._SECRET_VERIFY = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def SECRET_RAW_ACCESS_CODE(self) -> Optional[str]:
        """A code which allows access to the `/raw` version of the page."""
        return self._SECRET_RAW_ACCESS_CODE

    @SECRET_RAW_ACCESS_CODE.setter
    def SECRET_RAW_ACCESS_CODE(self, value: Optional[str]) -> None:
        self._SECRET_RAW_ACCESS_CODE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def SECRET_EMAIL_ADDRESS(self) -> Optional[str]:
        """The email address to recover the page if you lose access."""
        return self._SECRET_EMAIL_ADDRESS

    @SECRET_EMAIL_ADDRESS.setter
    def SECRET_EMAIL_ADDRESS(self, value: Optional[str]) -> None:
        self._SECRET_EMAIL_ADDRESS = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def CONTAINER_PADDING(self) -> Optional[list[str]]:
        """The internal spacing between the main container and the content."""
        return self._CONTAINER_PADDING

    @CONTAINER_PADDING.setter
    def CONTAINER_PADDING(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_PADDING = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTAINER_MAX_WIDTH(self) -> Optional[str]:
        """Limits and centers the content container's width."""
        return self._CONTAINER_MAX_WIDTH

    @CONTAINER_MAX_WIDTH.setter
    def CONTAINER_MAX_WIDTH(self, value: Optional[str]) -> None:
        self._CONTAINER_MAX_WIDTH = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def CONTAINER_INNER_FOREGROUND_COLOR(self) -> Optional[list[str]]:
        """The color of the inner foreground."""
        return self._CONTAINER_INNER_FOREGROUND_COLOR

    @CONTAINER_INNER_FOREGROUND_COLOR.setter
    def CONTAINER_INNER_FOREGROUND_COLOR(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_INNER_FOREGROUND_COLOR = [stripped for val in value if (stripped := val.replace(" ", ""))] if value else None
        self.validate()

    @property
    def CONTAINER_INNER_BACKGROUND_COLOR(self) -> Optional[list[str]]:
        """The color of the inner background."""
        return self._CONTAINER_INNER_BACKGROUND_COLOR

    @CONTAINER_INNER_BACKGROUND_COLOR.setter
    def CONTAINER_INNER_BACKGROUND_COLOR(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_INNER_BACKGROUND_COLOR = [stripped for val in value if (stripped := val.replace(" ", ""))] if value else None
        self.validate()

    @property
    def CONTAINER_INNER_BACKGROUND_IMAGE(self) -> Optional[str]:
        """The image of the inner background."""
        return self._CONTAINER_INNER_BACKGROUND_IMAGE

    @CONTAINER_INNER_BACKGROUND_IMAGE.setter
    def CONTAINER_INNER_BACKGROUND_IMAGE(self, value: Optional[str]) -> None:
        self._CONTAINER_INNER_BACKGROUND_IMAGE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT(
        self,
    ) -> Optional[Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]]:
        """The repeat style of the inner background image."""
        return self._CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT

    @CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT.setter
    def CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT(self, value: Optional[Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]]) -> None:
        self._CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT = value
        self.validate()

    @property
    def CONTAINER_INNER_BACKGROUND_IMAGE_POSITION(
        self,
    ) -> Optional[Literal["center", "left", "right", "top", "bottom"]]:
        """The position of the inner background image."""
        return self._CONTAINER_INNER_BACKGROUND_IMAGE_POSITION

    @CONTAINER_INNER_BACKGROUND_IMAGE_POSITION.setter
    def CONTAINER_INNER_BACKGROUND_IMAGE_POSITION(self, value: Optional[Literal["center", "left", "right", "top", "bottom"]]) -> None:
        self._CONTAINER_INNER_BACKGROUND_IMAGE_POSITION = value
        self.validate()

    @property
    def CONTAINER_INNER_BACKGROUND_IMAGE_SIZE(self) -> Optional[Literal["contain", "cover"] | str]:
        """The size of the inner background image."""
        return self._CONTAINER_INNER_BACKGROUND_IMAGE_SIZE

    @CONTAINER_INNER_BACKGROUND_IMAGE_SIZE.setter
    def CONTAINER_INNER_BACKGROUND_IMAGE_SIZE(self, value: Optional[Literal["contain", "cover"] | str]) -> None:
        self._CONTAINER_INNER_BACKGROUND_IMAGE_SIZE = value
        self.validate()

    @property
    def CONTAINER_OUTER_FOREGROUND_COLOR(self) -> Optional[list[str]]:
        """The color of the outer foreground."""
        return self._CONTAINER_OUTER_FOREGROUND_COLOR

    @CONTAINER_OUTER_FOREGROUND_COLOR.setter
    def CONTAINER_OUTER_FOREGROUND_COLOR(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_OUTER_FOREGROUND_COLOR = [stripped for val in value if (stripped := val.replace(" ", ""))] if value else None
        self.validate()

    @property
    def CONTAINER_OUTER_BACKGROUND_COLOR(self) -> Optional[list[str]]:
        """The color of the outer background."""
        return self._CONTAINER_OUTER_BACKGROUND_COLOR

    @CONTAINER_OUTER_BACKGROUND_COLOR.setter
    def CONTAINER_OUTER_BACKGROUND_COLOR(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_OUTER_BACKGROUND_COLOR = [stripped for val in value if (stripped := val.replace(" ", ""))] if value else None
        self.validate()

    @property
    def CONTAINER_OUTER_BACKGROUND_IMAGE(self) -> Optional[str]:
        """The image of the outer background."""
        return self._CONTAINER_OUTER_BACKGROUND_IMAGE

    @CONTAINER_OUTER_BACKGROUND_IMAGE.setter
    def CONTAINER_OUTER_BACKGROUND_IMAGE(self, value: Optional[str]) -> None:
        self._CONTAINER_OUTER_BACKGROUND_IMAGE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT(
        self,
    ) -> Optional[Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]]:
        """The repeat style of the outer background image."""
        return self._CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT

    @CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT.setter
    def CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT(self, value: Optional[Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]]) -> None:
        self._CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT = value
        self.validate()

    @property
    def CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION(
        self,
    ) -> Optional[Literal["center", "left", "right", "top", "bottom"]]:
        """The position of the outer background image."""
        return self._CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION

    @CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION.setter
    def CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION(self, value: Optional[Literal["center", "left", "right", "top", "bottom"]]) -> None:
        self._CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION = value
        self.validate()

    @property
    def CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE(self) -> Optional[str]:
        """The size of the outer background image."""
        return self._CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE

    @CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE.setter
    def CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE(self, value: Optional[str]) -> None:
        self._CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def CONTAINER_BORDER_IMAGE(self) -> Optional[str]:
        """The image of the container border."""
        return self._CONTAINER_BORDER_IMAGE

    @CONTAINER_BORDER_IMAGE.setter
    def CONTAINER_BORDER_IMAGE(self, value: Optional[str]) -> None:
        self._CONTAINER_BORDER_IMAGE = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def CONTAINER_BORDER_IMAGE_SLICE(self) -> Optional[list[str]]:
        """Controls how the border image is cut up and displayed."""
        return self._CONTAINER_BORDER_IMAGE_SLICE

    @CONTAINER_BORDER_IMAGE_SLICE.setter
    def CONTAINER_BORDER_IMAGE_SLICE(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_BORDER_IMAGE_SLICE = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTAINER_BORDER_IMAGE_WIDTH(self) -> Optional[list[str]]:
        """The width of the container border image."""
        return self._CONTAINER_BORDER_IMAGE_WIDTH

    @CONTAINER_BORDER_IMAGE_WIDTH.setter
    def CONTAINER_BORDER_IMAGE_WIDTH(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_BORDER_IMAGE_WIDTH = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTAINER_BORDER_IMAGE_OUTSET(self) -> Optional[list[str]]:
        """Controls where the border image appears in relation to the edges of the container."""
        return self._CONTAINER_BORDER_IMAGE_OUTSET

    @CONTAINER_BORDER_IMAGE_OUTSET.setter
    def CONTAINER_BORDER_IMAGE_OUTSET(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_BORDER_IMAGE_OUTSET = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTAINER_BORDER_IMAGE_REPEAT(self) -> Optional[list[str]]:
        """Controls how the border image is repeated."""
        return self._CONTAINER_BORDER_IMAGE_REPEAT

    @CONTAINER_BORDER_IMAGE_REPEAT.setter
    def CONTAINER_BORDER_IMAGE_REPEAT(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_BORDER_IMAGE_REPEAT = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTAINER_BORDER_COLOR(self) -> Optional[list[str]]:
        """The color of the container border."""
        return self._CONTAINER_BORDER_COLOR

    @CONTAINER_BORDER_COLOR.setter
    def CONTAINER_BORDER_COLOR(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_BORDER_COLOR = [stripped for val in value if (stripped := val.replace(" ", ""))] if value else None
        self.validate()

    @property
    def CONTAINER_BORDER_WIDTH(self) -> Optional[list[str]]:
        """The width of the container border."""
        return self._CONTAINER_BORDER_WIDTH

    @CONTAINER_BORDER_WIDTH.setter
    def CONTAINER_BORDER_WIDTH(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_BORDER_WIDTH = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTAINER_BORDER_STYLE(
        self,
    ) -> Optional[list[Literal["dotted", "dashed", "solid", "double", "groove", "ridge", "inset", "outset"]]]:
        """The style of the container border."""
        return self._CONTAINER_BORDER_STYLE

    @CONTAINER_BORDER_STYLE.setter
    def CONTAINER_BORDER_STYLE(
        self,
        value: Optional[list[Literal["dotted", "dashed", "solid", "double", "groove", "ridge", "inset", "outset"]]],
    ) -> None:
        self._CONTAINER_BORDER_STYLE = value
        self.validate()

    @property
    def CONTAINER_BORDER_RADIUS(self) -> Optional[list[str]]:
        """The radius of the container border."""
        return self._CONTAINER_BORDER_RADIUS

    @CONTAINER_BORDER_RADIUS.setter
    def CONTAINER_BORDER_RADIUS(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_BORDER_RADIUS = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTAINER_SHADOW_COLOR(self) -> Optional[str]:
        """The color of the container shadow."""
        return self._CONTAINER_SHADOW_COLOR

    @CONTAINER_SHADOW_COLOR.setter
    def CONTAINER_SHADOW_COLOR(self, value: Optional[str]) -> None:
        self._CONTAINER_SHADOW_COLOR = value.replace(" ", "") if value and value.replace(" ", "") else None
        self.validate()

    @property
    def CONTAINER_SHADOW_OFFSET(self) -> Optional[list[str]]:
        """The offset of the container shadow."""
        return self._CONTAINER_SHADOW_OFFSET

    @CONTAINER_SHADOW_OFFSET.setter
    def CONTAINER_SHADOW_OFFSET(self, value: Optional[list[str]]) -> None:
        self._CONTAINER_SHADOW_OFFSET = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTAINER_SHADOW_SPREAD(self) -> Optional[str]:
        """The spread of the container shadow."""
        return self._CONTAINER_SHADOW_SPREAD

    @CONTAINER_SHADOW_SPREAD.setter
    def CONTAINER_SHADOW_SPREAD(self, value: Optional[str]) -> None:
        self._CONTAINER_SHADOW_SPREAD = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def CONTAINER_SHADOW_BLUR(self) -> Optional[str]:
        """The blur of the container shadow."""
        return self._CONTAINER_SHADOW_BLUR

    @CONTAINER_SHADOW_BLUR.setter
    def CONTAINER_SHADOW_BLUR(self, value: Optional[str]) -> None:
        self._CONTAINER_SHADOW_BLUR = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def CONTENT_FONT(self) -> Optional[list[str]]:
        """The font of the content."""
        return self._CONTENT_FONT

    @CONTENT_FONT.setter
    def CONTENT_FONT(self, value: Optional[list[str]]) -> None:
        self._CONTENT_FONT = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTENT_FONT_WEIGHT(
        self,
    ) -> Optional[list[Literal["bold", "bolder", "lighter", "normal", "100", "200", "300", "400", "500", "600", "700", "800", "900"]]]:
        """The boldness of the content font."""
        return self._CONTENT_FONT_WEIGHT

    @CONTENT_FONT_WEIGHT.setter
    def CONTENT_FONT_WEIGHT(
        self,
        value: Optional[list[Literal["bold", "bolder", "lighter", "normal", "100", "200", "300", "400", "500", "600", "700", "800", "900"]]],
    ) -> None:
        self._CONTENT_FONT_WEIGHT = value
        self.validate()

    @property
    def CONTENT_TEXT_DIRECTION(self) -> Optional[Literal["ltr", "rtl"]]:
        """The direction of the content text."""
        return self._CONTENT_TEXT_DIRECTION

    @CONTENT_TEXT_DIRECTION.setter
    def CONTENT_TEXT_DIRECTION(self, value: Optional[Literal["ltr", "rtl"]]) -> None:
        self._CONTENT_TEXT_DIRECTION = value
        self.validate()

    @property
    def CONTENT_TEXT_SIZE(self) -> Optional[list[str]]:
        """The size of the content text."""
        return self._CONTENT_TEXT_SIZE

    @CONTENT_TEXT_SIZE.setter
    def CONTENT_TEXT_SIZE(self, value: Optional[list[str]]) -> None:
        self._CONTENT_TEXT_SIZE = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTENT_TEXT_ALIGN(self) -> Optional[Literal["right", "center", "justify"]]:
        """The alignment of the content text."""
        return self._CONTENT_TEXT_ALIGN

    @CONTENT_TEXT_ALIGN.setter
    def CONTENT_TEXT_ALIGN(self, value: Optional[Literal["right", "center", "justify"]]) -> None:
        self._CONTENT_TEXT_ALIGN = value
        self.validate()

    @property
    def CONTENT_TEXT_SHADOW_COLOR(self) -> Optional[str]:
        """The color of the content text shadow."""
        return self._CONTENT_TEXT_SHADOW_COLOR

    @CONTENT_TEXT_SHADOW_COLOR.setter
    def CONTENT_TEXT_SHADOW_COLOR(self, value: Optional[str]) -> None:
        self._CONTENT_TEXT_SHADOW_COLOR = value.replace(" ", "") if value and value.replace(" ", "") else None
        self.validate()

    @property
    def CONTENT_TEXT_SHADOW_OFFSET(self) -> Optional[list[str]]:
        """The offset of the content text shadow."""
        return self._CONTENT_TEXT_SHADOW_OFFSET

    @CONTENT_TEXT_SHADOW_OFFSET.setter
    def CONTENT_TEXT_SHADOW_OFFSET(self, value: Optional[list[str]]) -> None:
        self._CONTENT_TEXT_SHADOW_OFFSET = [val.strip() for val in value if val.strip()] if value else None
        self.validate()

    @property
    def CONTENT_TEXT_SHADOW_BLUR(self) -> Optional[str]:
        """The blur of the content text shadow."""
        return self._CONTENT_TEXT_SHADOW_BLUR

    @CONTENT_TEXT_SHADOW_BLUR.setter
    def CONTENT_TEXT_SHADOW_BLUR(self, value: Optional[str]) -> None:
        self._CONTENT_TEXT_SHADOW_BLUR = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def CONTENT_TEXT_COLOR(self) -> Optional[list[str]]:
        """The base color for page text. Inline colors will override this."""
        return self._CONTENT_TEXT_COLOR

    @CONTENT_TEXT_COLOR.setter
    def CONTENT_TEXT_COLOR(self, value: Optional[list[str]]) -> None:
        self._CONTENT_TEXT_COLOR = [stripped for val in value if (stripped := val.replace(" ", ""))] if value else None
        self.validate()

    @property
    def CONTENT_LINK_COLOR(self) -> Optional[list[str]]:
        """The color of links in the content."""
        return self._CONTENT_LINK_COLOR

    @CONTENT_LINK_COLOR.setter
    def CONTENT_LINK_COLOR(self, value: Optional[list[str]]) -> None:
        self._CONTENT_LINK_COLOR = [stripped for val in value if (stripped := val.replace(" ", ""))] if value else None
        self.validate()

    @property
    def CONTENT_BULLET_COLOR(self) -> Optional[list[str]]:
        """The color of bullet points in the content."""
        return self._CONTENT_BULLET_COLOR

    @CONTENT_BULLET_COLOR.setter
    def CONTENT_BULLET_COLOR(self, value: Optional[list[str]]) -> None:
        self._CONTENT_BULLET_COLOR = [stripped for val in value if (stripped := val.replace(" ", ""))] if value else None
        self.validate()

    @property
    def CONTENT_LINK_BEHAVIOR(self) -> Optional[list[Literal["same", "new"]]]:
        """The behavior of links in the content."""
        return self._CONTENT_LINK_BEHAVIOR

    @CONTENT_LINK_BEHAVIOR.setter
    def CONTENT_LINK_BEHAVIOR(self, value: Optional[list[Literal["same", "new"]]]) -> None:
        self._CONTENT_LINK_BEHAVIOR = value
        self.validate()

    @property
    def SAFETY_PAGE_WARNING(self) -> Optional[list[Literal["adult", "sensitive", "epilepsy", "custom"]]]:
        """Adds a warning popup to your page before allowing visitors to view."""
        return self._SAFETY_PAGE_WARNING

    @SAFETY_PAGE_WARNING.setter
    def SAFETY_PAGE_WARNING(self, value: Optional[list[Literal["adult", "sensitive", "epilepsy", "custom"]]]) -> None:
        self._SAFETY_PAGE_WARNING = value
        self.validate()

    @property
    def SAFETY_PAGE_WARNING_DESCRIPTION(self) -> Optional[str]:
        """Provide your own text to the warning popup created by SAFETY_PAGE_WARNING."""
        return self._SAFETY_PAGE_WARNING_DESCRIPTION

    @SAFETY_PAGE_WARNING_DESCRIPTION.setter
    def SAFETY_PAGE_WARNING_DESCRIPTION(self, value: Optional[str]) -> None:
        self._SAFETY_PAGE_WARNING_DESCRIPTION = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def SAFETY_MEDIA_BLUR(self) -> Optional[bool]:
        """Blurs all images in your page and requires them to be clicked before showing."""
        return self._SAFETY_MEDIA_BLUR

    @SAFETY_MEDIA_BLUR.setter
    def SAFETY_MEDIA_BLUR(self, value: Optional[bool]) -> None:
        self._SAFETY_MEDIA_BLUR = value
        self.validate()

    @property
    def SAFETY_LINK_WARNING(self) -> Optional[list[Literal["adult", "epilepsy", "sensitive"]]]:
        """Triggers a popup when clicking on a link within your content."""
        return self._SAFETY_LINK_WARNING

    @SAFETY_LINK_WARNING.setter
    def SAFETY_LINK_WARNING(self, value: Optional[list[Literal["adult", "epilepsy", "sensitive"]]]) -> None:
        self._SAFETY_LINK_WARNING = value
        self.validate()

    @property
    def SAFETY_LINK_WARNING_DESCRIPTION(self) -> Optional[str]:
        """Provide your own text to the link warning popup."""
        return self._SAFETY_LINK_WARNING_DESCRIPTION

    @SAFETY_LINK_WARNING_DESCRIPTION.setter
    def SAFETY_LINK_WARNING_DESCRIPTION(self, value: Optional[str]) -> None:
        self._SAFETY_LINK_WARNING_DESCRIPTION = value.strip() if value and value.strip() else None
        self.validate()

    @property
    def SAFETY_PAGE_FLAG(self) -> Optional[list[Literal["adult", "epilepsy", "sensitive"]]]:
        """Creates a visual icon on your page to inform readers that a page contains certain material."""
        return self._SAFETY_PAGE_FLAG

    @SAFETY_PAGE_FLAG.setter
    def SAFETY_PAGE_FLAG(self, value: Optional[list[Literal["adult", "epilepsy", "sensitive"]]]) -> None:
        self._SAFETY_PAGE_FLAG = value
        self.validate()

    def _check_css_size(
        self,
        *,
        rule: str,
        values: list[str] | str,
        max_values: int,
        max_length: int,
        allowed_terms: list[str],
        unitless_bounds: Optional[tuple[float, float, int]],
        px_bounds: Optional[tuple[float, float, int]],
        percent_bounds: Optional[tuple[float, float, int]],
        vh_bounds: Optional[tuple[float, float, int]],
        hw_bounds: Optional[tuple[float, float, int]],
        rem_bounds: Optional[tuple[float, float, int]],
    ) -> list[str]:
        errors: list[str] = []
        values = values if isinstance(values, list) else [values]

        if not values:
            errors.append(f"{rule} must have at least one value.")
        elif len(values) > max_values:
            errors.append(f"{rule} must have {max_values} values or less.")

        if len(" ".join(values)) > max_length:
            errors.append(f"{rule} must have a total length of {max_length} characters or less.")

        for value in values:
            match: Optional[re.Match] = CSS_SIZE_REGEX.match(value)

            if not match:
                if not allowed_terms:
                    errors.append(f"{rule} must be a valid CSS size.")
                elif value not in allowed_terms:
                    errors.append(f"{rule} must be a valid CSS size or one of the following: {', '.join(allowed_terms)}.")
                continue

            number_str: str = match.group(1)
            number: float = float(number_str)
            unit: Optional[str] = match.group(2)

            if not unit:
                if not unitless_bounds:
                    errors.append(f"{rule} values must have units.")
                elif not unitless_bounds[0] <= number <= unitless_bounds[1]:
                    errors.append(f"{rule} unitless values must be between {unitless_bounds[0]} and {unitless_bounds[1]}.")
            elif unit == "px":
                if not px_bounds:
                    errors.append(f"{rule} values do not support px units.")
                elif not px_bounds[0] <= number <= px_bounds[1]:
                    errors.append(f"{rule} px values must be between {px_bounds[0]} and {px_bounds[1]}.")
            elif unit == "%":
                if not percent_bounds:
                    errors.append(f"{rule} values do not support % units.")
                elif not percent_bounds[0] <= number <= percent_bounds[1]:
                    errors.append(f"{rule} % values must be between {percent_bounds[0]} and {percent_bounds[1]}.")
            elif unit == "vh":
                if not vh_bounds:
                    errors.append(f"{rule} values do not support vh units.")
                elif not vh_bounds[0] <= number <= vh_bounds[1]:
                    errors.append(f"{rule} vh values must be between {vh_bounds[0]} and {vh_bounds[1]}.")
            elif unit == "hw":
                if not hw_bounds:
                    errors.append(f"{rule} values do not support hw units.")
                elif not hw_bounds[0] <= number <= hw_bounds[1]:
                    errors.append(f"{rule} hw values must be between {hw_bounds[0]} and {hw_bounds[1]}.")
            elif unit == "rem":
                if not rem_bounds:
                    errors.append(f"{rule} values do not support rem units.")
                elif not rem_bounds[0] <= number <= rem_bounds[1]:
                    errors.append(f"{rule} rem values must be between {rem_bounds[0]} and {rem_bounds[1]}.")

        seen_errors: list[str] = []

        for error in errors:
            if error not in seen_errors:
                seen_errors.append(error)

        return seen_errors

    def _check_css_color(self, *, rule: str, values: list[str] | str, max_values: int, max_length: int) -> list[str]:
        errors: list[str] = []
        values = values if isinstance(values, list) else [values]

        if not values:
            errors.append(f"{rule} must have at least one value.")
        elif len(values) > max_values:
            errors.append(f"{rule} must have {max_values} values or less.")

        if len(" ".join(values)) > max_length:
            errors.append(f"{rule} must have a total length of {max_length} characters or less.")

        if any(not HEX_REGEX.match(value) and not RGBA_REGEX.match(value) and value not in CSS_COLOR_NAMES for value in values):
            errors.append(f"{rule} values must be valid HEX codes, RGBA values, or CSS color names.")

        return errors

    def _get_type(self, variable: str) -> str:
        type_mapping = {
            "PAGE_TITLE": "str",
            "PAGE_DESCRIPTION": "str",
            "PAGE_IMAGE": "str",
            "PAGE_ICON": "str",
            "SHARE_TITLE": "str",
            "SHARE_DESCRIPTION": "str",
            "SHARE_IMAGE": "str",
            "SHARE_TWITTER_TITLE": "str",
            "SHARE_TWITTER_DESCRIPTION": "str",
            "SHARE_TWITTER_IMAGE": "str",
            "OPTION_DISABLE_VIEWS": "bool",
            "OPTION_DISABLE_SEARCH_ENGINE": "bool",
            "OPTION_USE_ORIGINAL_PUB_DATE": "bool",
            "ACCESS_RECOMMENDED_THEME": "str",
            "ACCESS_EASY_READ": "str",
            "SECRET_VERIFY": "str",
            "SECRET_RAW_ACCESS_CODE": "str",
            "SECRET_EMAIL_ADDRESS": "str",
            "CONTAINER_PADDING": "list",
            "CONTAINER_MAX_WIDTH": "str",
            "CONTAINER_INNER_FOREGROUND_COLOR": "list",
            "CONTAINER_INNER_BACKGROUND_COLOR": "list",
            "CONTAINER_INNER_BACKGROUND_IMAGE": "str",
            "CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT": "str",
            "CONTAINER_INNER_BACKGROUND_IMAGE_POSITION": "str",
            "CONTAINER_INNER_BACKGROUND_IMAGE_SIZE": "str",
            "CONTAINER_OUTER_FOREGROUND_COLOR": "list",
            "CONTAINER_OUTER_BACKGROUND_COLOR": "list",
            "CONTAINER_OUTER_BACKGROUND_IMAGE": "str",
            "CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT": "str",
            "CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION": "str",
            "CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE": "str",
            "CONTAINER_BORDER_IMAGE": "str",
            "CONTAINER_BORDER_IMAGE_SLICE": "list",
            "CONTAINER_BORDER_IMAGE_WIDTH": "list",
            "CONTAINER_BORDER_IMAGE_OUTSET": "list",
            "CONTAINER_BORDER_IMAGE_REPEAT": "list",
            "CONTAINER_BORDER_COLOR": "list",
            "CONTAINER_BORDER_WIDTH": "list",
            "CONTAINER_BORDER_STYLE": "list",
            "CONTAINER_BORDER_RADIUS": "list",
            "CONTAINER_SHADOW_COLOR": "str",
            "CONTAINER_SHADOW_OFFSET": "list",
            "CONTAINER_SHADOW_SPREAD": "str",
            "CONTAINER_SHADOW_BLUR": "str",
            "CONTENT_FONT": "list",
            "CONTENT_FONT_WEIGHT": "list",
            "CONTENT_TEXT_DIRECTION": "str",
            "CONTENT_TEXT_SIZE": "list",
            "CONTENT_TEXT_ALIGN": "str",
            "CONTENT_TEXT_SHADOW_COLOR": "str",
            "CONTENT_TEXT_SHADOW_OFFSET": "list",
            "CONTENT_TEXT_SHADOW_BLUR": "str",
            "CONTENT_TEXT_COLOR": "list",
            "CONTENT_LINK_COLOR": "list",
            "CONTENT_BULLET_COLOR": "list",
            "CONTENT_LINK_BEHAVIOR": "list",
            "SAFETY_PAGE_WARNING": "list",
            "SAFETY_PAGE_WARNING_DESCRIPTION": "str",
            "SAFETY_MEDIA_BLUR": "bool",
            "SAFETY_LINK_WARNING": "list",
            "SAFETY_LINK_WARNING_DESCRIPTION": "str",
            "SAFETY_PAGE_FLAG": "list",
        }

        return type_mapping.get(variable, "UNKNOWN")

    def validate(self) -> None:
        """
        Validate all locally validatable metadata attributes.

        #### Notes
        - If a non-existent rentry url is set for `ACCESS_EASY_READ`, the rentry API will reject the value.
        - If an invalid Google Font is set for `CONTENT_FONT`, the rentry API will silently ignore the value.

        #### Raises
        - `RentryInvalidMetadataError` when one or more metadata attributes are invalid.
        """

        errors: list[str] = []

        if self._PAGE_TITLE and len(self._PAGE_TITLE) > 60:
            errors.append("PAGE_TITLE must be 60 characters or less.")

        if self._PAGE_DESCRIPTION and len(self._PAGE_DESCRIPTION) > 160:
            errors.append("PAGE_DESCRIPTION must be 160 characters or less.")

        if self._PAGE_IMAGE:
            if len(self._PAGE_IMAGE) > 1_000:
                errors.append("PAGE_IMAGE must be 1,000 characters or less.")

            if not ANY_URL_REGEX.match(self._PAGE_IMAGE):
                errors.append("PAGE_IMAGE must be a valid URL.")

        if self._PAGE_ICON:
            if len(self._PAGE_ICON) > 1_000:
                errors.append("PAGE_ICON must be 1,000 characters or less.")

            if not ANY_URL_REGEX.match(self._PAGE_ICON):
                errors.append("PAGE_ICON must be a valid URL.")

        if self._SHARE_TITLE and len(self._SHARE_TITLE) > 60:
            errors.append("SHARE_TITLE must be 60 characters or less.")

        if self._SHARE_DESCRIPTION and len(self._SHARE_DESCRIPTION) > 160:
            errors.append("SHARE_DESCRIPTION must be 160 characters or less.")

        if self._SHARE_IMAGE:
            if len(self._SHARE_IMAGE) > 1_000:
                errors.append("SHARE_IMAGE must be 1,000 characters or less.")

            if not ANY_URL_REGEX.match(self._SHARE_IMAGE):
                errors.append("SHARE_IMAGE must be a valid URL.")

        if self._SHARE_TWITTER_TITLE and len(self._SHARE_TWITTER_TITLE) > 60:
            errors.append("SHARE_TWITTER_TITLE must be 60 characters or less.")

        if self._SHARE_TWITTER_DESCRIPTION and len(self._SHARE_TWITTER_DESCRIPTION) > 160:
            errors.append("SHARE_TWITTER_DESCRIPTION must be 160 characters or less.")

        if self._SHARE_TWITTER_IMAGE:
            if len(self._SHARE_TWITTER_IMAGE) > 1_000:
                errors.append("SHARE_TWITTER_IMAGE must be 1,000 characters or less.")

            if not ANY_URL_REGEX.match(self._SHARE_TWITTER_IMAGE):
                errors.append("SHARE_TWITTER_IMAGE must be a valid URL.")

        if self._ACCESS_RECOMMENDED_THEME:
            valid_themes = ["dark", "light"]

            if self._ACCESS_RECOMMENDED_THEME not in valid_themes:
                errors.append('ACCESS_RECOMMENDED_THEME must be "dark" or "light".')

        if self._ACCESS_EASY_READ:
            if len(self._ACCESS_EASY_READ) > 300:
                errors.append("ACCESS_EASY_READ must be 300 characters or less.")

            if not RENTRY_PAGE_URL_REGEX.match(self._ACCESS_EASY_READ):
                errors.append("ACCESS_EASY_READ must be a valid rentry URL.")

        if self._SECRET_VERIFY and len(self._SECRET_VERIFY) > 3_000:
            errors.append("SECRET_VERIFY must be 3,000 characters or less.")

        if self._SECRET_RAW_ACCESS_CODE and len(self._SECRET_RAW_ACCESS_CODE) > 100:
            errors.append("SECRET_RAW_ACCESS_CODE must be 100 characters or less.")

        if self._SECRET_EMAIL_ADDRESS:
            if len(self._SECRET_EMAIL_ADDRESS) > 300:
                errors.append("SECRET_EMAIL_ADDRESS must be 300 characters or less.")

            if not EMAIL_REGEX.match(self._SECRET_EMAIL_ADDRESS) and not SECRET_REGEX.match(self._SECRET_EMAIL_ADDRESS):
                errors.append("SECRET_EMAIL_ADDRESS must be a valid email address.")

        if self._CONTAINER_PADDING:
            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_PADDING",
                    values=self._CONTAINER_PADDING,
                    max_values=4,
                    max_length=64,
                    allowed_terms=[],
                    unitless_bounds=(0, 40, 0),
                    px_bounds=(0, 40, 0),
                    percent_bounds=(0, 25, 3),
                    vh_bounds=(0, 15, 4),
                    hw_bounds=(0, 20, 4),
                    rem_bounds=(0, 7, 4),
                )
            )

        if self._CONTAINER_MAX_WIDTH:
            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_MAX_WIDTH",
                    values=self._CONTAINER_MAX_WIDTH,
                    max_values=1,
                    max_length=16,
                    allowed_terms=[],
                    unitless_bounds=(100, 1600, 0),
                    px_bounds=(100, 1600, 0),
                    percent_bounds=(10, 100, 3),
                    vh_bounds=(10, 100, 4),
                    hw_bounds=(10, 100, 4),
                    rem_bounds=(3, 25, 4),
                )
            )

        if self._CONTAINER_INNER_FOREGROUND_COLOR:
            errors.extend(
                self._check_css_color(
                    rule="CONTAINER_INNER_FOREGROUND_COLOR",
                    values=self._CONTAINER_INNER_FOREGROUND_COLOR,
                    max_values=2,
                    max_length=32,
                )
            )

        if self._CONTAINER_INNER_BACKGROUND_COLOR:
            errors.extend(
                self._check_css_color(
                    rule="CONTAINER_INNER_BACKGROUND_COLOR",
                    values=self._CONTAINER_INNER_BACKGROUND_COLOR,
                    max_values=2,
                    max_length=32,
                )
            )

        if self._CONTAINER_INNER_BACKGROUND_IMAGE:
            if len(self._CONTAINER_INNER_BACKGROUND_IMAGE) > 1_000:
                errors.append("CONTAINER_INNER_BACKGROUND_IMAGE must be 1,000 characters or less.")

            if not ANY_URL_REGEX.match(self._CONTAINER_INNER_BACKGROUND_IMAGE):
                errors.append("CONTAINER_INNER_BACKGROUND_IMAGE must be a valid URL.")

        if self._CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT:
            valid_repeats = ["no-repeat", "repeat-x", "repeat-y", "round", "space"]

            if self._CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT not in valid_repeats:
                errors.append('CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT must be "no-repeat", "repeat-x", "repeat-y", "round", or "space".')

        if self._CONTAINER_INNER_BACKGROUND_IMAGE_POSITION:
            valid_positions = ["center", "left", "right", "top", "bottom"]

            if self._CONTAINER_INNER_BACKGROUND_IMAGE_POSITION not in valid_positions:
                errors.append('CONTAINER_INNER_BACKGROUND_IMAGE_POSITION must be "center", "left", "right", "top", or "bottom".')

        if self._CONTAINER_INNER_BACKGROUND_IMAGE_SIZE:
            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_INNER_BACKGROUND_IMAGE_SIZE",
                    values=self._CONTAINER_INNER_BACKGROUND_IMAGE_SIZE,
                    max_values=1,
                    max_length=16,
                    allowed_terms=["contain", "cover"],
                    unitless_bounds=(1, 3000, 0),
                    px_bounds=(1, 3000, 0),
                    percent_bounds=(0.1, 150, 3),
                    vh_bounds=(0.1, 200, 4),
                    hw_bounds=(0.1, 200, 4),
                    rem_bounds=(0.1, 50, 4),
                )
            )

        if self._CONTAINER_OUTER_FOREGROUND_COLOR:
            errors.extend(
                self._check_css_color(
                    rule="CONTAINER_OUTER_FOREGROUND_COLOR",
                    values=self._CONTAINER_OUTER_FOREGROUND_COLOR,
                    max_values=2,
                    max_length=32,
                )
            )

        if self._CONTAINER_OUTER_BACKGROUND_COLOR:
            errors.extend(
                self._check_css_color(
                    rule="CONTAINER_OUTER_BACKGROUND_COLOR",
                    values=self._CONTAINER_OUTER_BACKGROUND_COLOR,
                    max_values=2,
                    max_length=32,
                )
            )

        if self._CONTAINER_OUTER_BACKGROUND_IMAGE:
            if len(self._CONTAINER_OUTER_BACKGROUND_IMAGE) > 1_000:
                errors.append("CONTAINER_OUTER_BACKGROUND_IMAGE must be 1,000 characters or less.")

            if not ANY_URL_REGEX.match(self._CONTAINER_OUTER_BACKGROUND_IMAGE):
                errors.append("CONTAINER_OUTER_BACKGROUND_IMAGE must be a valid URL.")

        if self._CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT:
            valid_repeats = ["no-repeat", "repeat-x", "repeat-y", "round", "space"]

            if self._CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT not in valid_repeats:
                errors.append('CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT must be "no-repeat", "repeat-x", "repeat-y", "round", or "space".')

        if self._CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION:
            valid_positions = ["center", "left", "right", "top", "bottom"]

            if self._CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION not in valid_positions:
                errors.append('CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION must be "center", "left", "right", "top", or "bottom".')

        if self._CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE:
            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE",
                    values=self._CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE,
                    max_values=1,
                    max_length=16,
                    allowed_terms=["contain", "cover"],
                    unitless_bounds=(1, 3000, 0),
                    px_bounds=(1, 3000, 0),
                    percent_bounds=(0.1, 150, 3),
                    vh_bounds=(0.1, 200, 4),
                    hw_bounds=(0.1, 200, 4),
                    rem_bounds=(0.1, 50, 4),
                )
            )

        if self._CONTAINER_BORDER_IMAGE:
            if len(self._CONTAINER_BORDER_IMAGE) > 1_000:
                errors.append("CONTAINER_BORDER_IMAGE must be 1,000 characters or less.")

            if not ANY_URL_REGEX.match(self._CONTAINER_BORDER_IMAGE):
                errors.append("CONTAINER_BORDER_IMAGE must be a valid URL.")

        if self._CONTAINER_BORDER_IMAGE_SLICE:
            if not self._CONTAINER_BORDER_IMAGE or not self._CONTAINER_BORDER_IMAGE_WIDTH:
                errors.append("CONTAINER_BORDER_IMAGE_SLICE requires CONTAINER_BORDER_IMAGE and CONTAINER_BORDER_IMAGE_WIDTH.")

            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_BORDER_IMAGE_SLICE",
                    values=self._CONTAINER_BORDER_IMAGE_SLICE,
                    max_values=4,
                    max_length=64,
                    allowed_terms=["fill"],
                    unitless_bounds=(0, 20, 0),
                    px_bounds=None,
                    percent_bounds=(0, 100, 3),
                    vh_bounds=None,
                    hw_bounds=None,
                    rem_bounds=None,
                )
            )

        if self._CONTAINER_BORDER_IMAGE_WIDTH:
            if not self._CONTAINER_BORDER_IMAGE:
                errors.append("CONTAINER_BORDER_IMAGE_WIDTH requires CONTAINER_BORDER_IMAGE.")

            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_BORDER_IMAGE_WIDTH",
                    values=self._CONTAINER_BORDER_IMAGE_WIDTH,
                    max_values=4,
                    max_length=64,
                    allowed_terms=["auto"],
                    unitless_bounds=(0, 20, 0),
                    px_bounds=(0, 30, 0),
                    percent_bounds=(0, 100, 3),
                    vh_bounds=None,
                    hw_bounds=None,
                    rem_bounds=None,
                )
            )

        if self._CONTAINER_BORDER_IMAGE_OUTSET:
            if not self._CONTAINER_BORDER_IMAGE or not self._CONTAINER_BORDER_IMAGE_WIDTH:
                errors.append("CONTAINER_BORDER_IMAGE_OUTSET requires CONTAINER_BORDER_IMAGE and CONTAINER_BORDER_IMAGE_WIDTH.")

            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_BORDER_IMAGE_OUTSET",
                    values=self._CONTAINER_BORDER_IMAGE_OUTSET,
                    max_values=4,
                    max_length=64,
                    allowed_terms=["auto"],
                    unitless_bounds=(0, 20, 0),
                    px_bounds=(0, 30, 0),
                    percent_bounds=None,
                    vh_bounds=None,
                    hw_bounds=None,
                    rem_bounds=None,
                )
            )

        if self._CONTAINER_BORDER_IMAGE_REPEAT:
            if not self._CONTAINER_BORDER_IMAGE or not self._CONTAINER_BORDER_IMAGE_WIDTH:
                errors.append("CONTAINER_BORDER_IMAGE_REPEAT requires CONTAINER_BORDER_IMAGE and CONTAINER_BORDER_IMAGE_WIDTH.")

            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_BORDER_IMAGE_REPEAT",
                    values=self._CONTAINER_BORDER_IMAGE_REPEAT,
                    max_values=2,
                    max_length=32,
                    allowed_terms=["stretch", "repeat", "round", "space"],
                    unitless_bounds=None,
                    px_bounds=None,
                    percent_bounds=None,
                    vh_bounds=None,
                    hw_bounds=None,
                    rem_bounds=None,
                )
            )

        if self._CONTAINER_BORDER_COLOR:
            if not self._CONTAINER_BORDER_WIDTH or not self._CONTAINER_BORDER_STYLE:
                errors.append("CONTAINER_BORDER_COLOR requires CONTAINER_BORDER_WIDTH and CONTAINER_BORDER_STYLE.")

            errors.extend(
                self._check_css_color(
                    rule="CONTAINER_BORDER_COLOR",
                    values=self._CONTAINER_BORDER_COLOR,
                    max_values=4,
                    max_length=120,
                )
            )

        if self._CONTAINER_BORDER_WIDTH:
            if not self._CONTAINER_BORDER_STYLE:
                errors.append("CONTAINER_BORDER_WIDTH requires CONTAINER_BORDER_STYLE.")

            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_BORDER_WIDTH",
                    values=self._CONTAINER_BORDER_WIDTH,
                    max_values=4,
                    max_length=64,
                    allowed_terms=[],
                    unitless_bounds=(0, 40, 0),
                    px_bounds=(0, 40, 0),
                    percent_bounds=(0, 15, 3),
                    vh_bounds=(0, 5, 4),
                    hw_bounds=(0, 5, 4),
                    rem_bounds=(0, 4, 4),
                )
            )

        if self._CONTAINER_BORDER_STYLE:
            if not self._CONTAINER_BORDER_WIDTH:
                errors.append("CONTAINER_BORDER_STYLE requires CONTAINER_BORDER_WIDTH.")

            valid_styles = ["dotted", "dashed", "solid", "double", "groove", "ridge", "inset", "outset"]

            if any(style not in valid_styles for style in self._CONTAINER_BORDER_STYLE):
                errors.append('CONTAINER_BORDER_STYLE must be "dotted", "dashed", "solid", "double", "groove", "ridge", "inset", or "outset".')

        if self._CONTAINER_BORDER_RADIUS:
            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_BORDER_RADIUS",
                    values=self._CONTAINER_BORDER_RADIUS,
                    max_values=4,
                    max_length=64,
                    allowed_terms=[],
                    unitless_bounds=(0, 200, 0),
                    px_bounds=(0, 200, 0),
                    percent_bounds=(0, 50, 3),
                    vh_bounds=(0, 40, 4),
                    hw_bounds=(0, 40, 4),
                    rem_bounds=(0, 30, 4),
                )
            )

        if self._CONTAINER_SHADOW_COLOR:
            if not self._CONTAINER_SHADOW_OFFSET and not self._CONTAINER_SHADOW_SPREAD and not self._CONTAINER_SHADOW_BLUR:
                errors.append("CONTAINER_SHADOW_COLOR requires CONTAINER_SHADOW_OFFSET, CONTAINER_SHADOW_SPREAD, or CONTAINER_SHADOW_BLUR.")

            errors.extend(self._check_css_color(rule="CONTAINER_SHADOW_COLOR", values=self._CONTAINER_SHADOW_COLOR, max_values=1, max_length=32))

        if self._CONTAINER_SHADOW_OFFSET:
            if not self._CONTAINER_SHADOW_COLOR:
                errors.append("CONTAINER_SHADOW_OFFSET requires CONTAINER_SHADOW_COLOR.")

            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_SHADOW_OFFSET",
                    values=self._CONTAINER_SHADOW_OFFSET,
                    max_values=2,
                    max_length=32,
                    allowed_terms=[],
                    unitless_bounds=(-15, 15, 0),
                    px_bounds=(-15, 15, 0),
                    percent_bounds=(-5, 5, 3),
                    vh_bounds=(-2, 2, 4),
                    hw_bounds=(-2, 2, 4),
                    rem_bounds=(-4, 2, 4),
                )
            )

        if self._CONTAINER_SHADOW_SPREAD:
            if not self._CONTAINER_SHADOW_COLOR:
                errors.append("CONTAINER_SHADOW_SPREAD requires CONTAINER_SHADOW_COLOR.")

            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_SHADOW_SPREAD",
                    values=self._CONTAINER_SHADOW_SPREAD,
                    max_values=1,
                    max_length=12,
                    allowed_terms=[],
                    unitless_bounds=(0, 30, 0),
                    px_bounds=(0, 30, 0),
                    percent_bounds=(0, 10, 3),
                    vh_bounds=(0, 5, 4),
                    hw_bounds=(0, 5, 4),
                    rem_bounds=(0, 3, 4),
                )
            )

        if self._CONTAINER_SHADOW_BLUR:
            if not self._CONTAINER_SHADOW_COLOR:
                errors.append("CONTAINER_SHADOW_BLUR requires CONTAINER_SHADOW_COLOR.")

            errors.extend(
                self._check_css_size(
                    rule="CONTAINER_SHADOW_BLUR",
                    values=self._CONTAINER_SHADOW_BLUR,
                    max_values=1,
                    max_length=12,
                    allowed_terms=[],
                    unitless_bounds=(0, 30, 0),
                    px_bounds=(0, 30, 0),
                    percent_bounds=(0, 10, 3),
                    vh_bounds=(0, 5, 4),
                    hw_bounds=(0, 5, 4),
                    rem_bounds=(0, 3, 4),
                )
            )

        if self._CONTENT_FONT:
            if len(" ".join(self._CONTENT_FONT)) > 1_000:
                errors.append("CONTENT_FONT must be 1,000 characters or less.")

            if len(self._CONTENT_FONT) > 2:
                errors.append("CONTENT_FONT must have 2 values or less.")

        if self._CONTENT_FONT_WEIGHT:
            if len(" ".join(self._CONTENT_FONT_WEIGHT)) > 24:
                errors.append("CONTENT_FONT_WEIGHT must have a total length of 24 characters or less.")

            if len(self._CONTENT_FONT_WEIGHT) > 2:
                errors.append("CONTENT_FONT_WEIGHT must have 2 values or less.")

            valid_weights = [
                "bold",
                "bolder",
                "lighter",
                "normal",
                "100",
                "200",
                "300",
                "400",
                "500",
                "600",
                "700",
                "800",
                "900",
            ]

            if any(weight not in valid_weights for weight in self._CONTENT_FONT_WEIGHT):
                errors.append('CONTENT_FONT_WEIGHT must be "bold", "bolder", "lighter", "normal", "100", "200", "300", "400", "500", "600", "700", "800", or "900".')

        if self._CONTENT_TEXT_DIRECTION and self._CONTENT_TEXT_DIRECTION not in ["ltr", "rtl"]:
            errors.append('CONTENT_TEXT_DIRECTION must be "ltr" or "rtl".')

        if self._CONTENT_TEXT_SIZE:
            errors.extend(
                self._check_css_size(
                    rule="CONTENT_TEXT_SIZE",
                    values=self._CONTENT_TEXT_SIZE,
                    max_values=12,
                    max_length=128,
                    allowed_terms=[],
                    unitless_bounds=(8, 64, 0),
                    px_bounds=(8, 64, 0),
                    percent_bounds=(10, 500, 3),
                    vh_bounds=(2, 10, 4),
                    hw_bounds=(2, 10, 4),
                    rem_bounds=(0.3, 8, 4),
                )
            )

        if self._CONTENT_TEXT_ALIGN and self._CONTENT_TEXT_ALIGN not in ["right", "center", "justify"]:
            errors.append('CONTENT_TEXT_ALIGN must be "right", "center", or "justify".')

        if self._CONTENT_TEXT_SHADOW_COLOR:
            if not self._CONTENT_TEXT_SHADOW_OFFSET:
                errors.append("CONTENT_TEXT_SHADOW_COLOR requires CONTENT_TEXT_SHADOW_OFFSET.")

            errors.extend(
                self._check_css_color(
                    rule="CONTENT_TEXT_SHADOW_COLOR",
                    values=self._CONTENT_TEXT_SHADOW_COLOR,
                    max_values=1,
                    max_length=32,
                )
            )

        if self._CONTENT_TEXT_SHADOW_OFFSET:
            if not self._CONTENT_TEXT_SHADOW_COLOR:
                errors.append("CONTENT_TEXT_SHADOW_OFFSET requires CONTENT_TEXT_SHADOW_COLOR.")

            errors.extend(
                self._check_css_size(
                    rule="CONTENT_TEXT_SHADOW_OFFSET",
                    values=self._CONTENT_TEXT_SHADOW_OFFSET,
                    max_values=2,
                    max_length=32,
                    allowed_terms=[],
                    unitless_bounds=(-15, 15, 0),
                    px_bounds=(-15, 15, 0),
                    percent_bounds=(-5, 5, 3),
                    vh_bounds=(-2, 2, 4),
                    hw_bounds=(-2, 2, 4),
                    rem_bounds=(-2, 2, 4),
                )
            )

        if self._CONTENT_TEXT_SHADOW_BLUR:
            if not self._CONTENT_TEXT_SHADOW_COLOR or not self._CONTENT_TEXT_SHADOW_OFFSET:
                errors.append("CONTENT_TEXT_SHADOW_BLUR requires CONTENT_TEXT_SHADOW_COLOR and CONTENT_TEXT_SHADOW_OFFSET.")

            errors.extend(
                self._check_css_size(
                    rule="CONTENT_TEXT_SHADOW_BLUR",
                    values=self._CONTENT_TEXT_SHADOW_BLUR,
                    max_values=1,
                    max_length=12,
                    allowed_terms=[],
                    unitless_bounds=(0, 30, 0),
                    px_bounds=(0, 30, 0),
                    percent_bounds=(0, 10, 3),
                    vh_bounds=(0, 5, 4),
                    hw_bounds=(0, 5, 4),
                    rem_bounds=(0, 3, 4),
                )
            )

        if self._CONTENT_TEXT_COLOR:
            errors.extend(
                self._check_css_color(
                    rule="CONTENT_TEXT_COLOR",
                    values=self._CONTENT_TEXT_COLOR,
                    max_values=2,
                    max_length=128,
                )
            )

        if self._CONTENT_LINK_COLOR:
            errors.extend(
                self._check_css_color(
                    rule="CONTENT_LINK_COLOR",
                    values=self._CONTENT_LINK_COLOR,
                    max_values=2,
                    max_length=16,
                )
            )

        if self._CONTENT_BULLET_COLOR:
            errors.extend(
                self._check_css_color(
                    rule="CONTENT_BULLET_COLOR",
                    values=self._CONTENT_BULLET_COLOR,
                    max_values=2,
                    max_length=16,
                )
            )

        if self._CONTENT_LINK_BEHAVIOR:
            if len(self._CONTENT_LINK_BEHAVIOR) > 2:
                errors.append("CONTENT_LINK_BEHAVIOR must have 2 values or less.")

            if any(behavior not in ["same", "new"] for behavior in self._CONTENT_LINK_BEHAVIOR):
                errors.append('CONTENT_LINK_BEHAVIOR must be "same" or "new".')

        if self._SAFETY_PAGE_WARNING:
            if len(self._SAFETY_PAGE_WARNING) > 4:
                errors.append("SAFETY_PAGE_WARNING must have 4 values or less.")

            if len(" ".join(self._SAFETY_PAGE_WARNING)) > 100:
                errors.append("SAFETY_PAGE_WARNING must be 100 characters or less.")

            if any(warning not in ["adult", "sensitive", "epilepsy", "custom"] for warning in self._SAFETY_PAGE_WARNING):
                errors.append('SAFETY_PAGE_WARNING must be "adult", "sensitive", "epilepsy", or "custom".')

        if self._SAFETY_PAGE_WARNING_DESCRIPTION and len(self._SAFETY_PAGE_WARNING_DESCRIPTION) > 240:
            errors.append("SAFETY_PAGE_WARNING_DESCRIPTION must be 240 characters or less.")

        if self._SAFETY_LINK_WARNING:
            if len(self._SAFETY_LINK_WARNING) > 3:
                errors.append("SAFETY_LINK_WARNING must have 3 values or less.")

            if len(" ".join(self._SAFETY_LINK_WARNING)) > 100:
                errors.append("SAFETY_LINK_WARNING must be 100 characters or less.")

            if any(warning not in ["adult", "epilepsy", "sensitive"] for warning in self._SAFETY_LINK_WARNING):
                errors.append('SAFETY_LINK_WARNING must be "adult", "epilepsy", or "sensitive".')

        if self._SAFETY_LINK_WARNING_DESCRIPTION and len(self._SAFETY_LINK_WARNING_DESCRIPTION) > 240:
            errors.append("SAFETY_LINK_WARNING_DESCRIPTION must be 240 characters or less.")

        if self._SAFETY_PAGE_FLAG:
            if len(self._SAFETY_PAGE_FLAG) > 3:
                errors.append("SAFETY_PAGE_FLAG must have 3 values or less.")

            if len(" ".join(self._SAFETY_PAGE_FLAG)) > 100:
                errors.append("SAFETY_PAGE_FLAG must be 100 characters or less.")

            if any(flag not in ["adult", "epilepsy", "sensitive"] for flag in self._SAFETY_PAGE_FLAG):
                errors.append('SAFETY_PAGE_FLAG must be "adult", "epilepsy", or "sensitive".')

        if errors:
            raise RentryInvalidMetadataError("\n".join(errors))

    def encode(self) -> str:
        """
        Encode the metadata to a JSON string for the rentry API.

        #### Returns
        - `str`: The metadata encoded as a JSON string for the rentry API.
        """

        def encode_value(val):
            if isinstance(val, list):
                return " ".join(val)

            return val

        return json.dumps({key.removeprefix("_"): encode_value(val) for key, val in self.__dict__.items() if val is not None})

    def decode(self, data: str | dict[str, Any]) -> None:
        """
        Decode the metadata from the rentry API.

        #### Arguments
        - data: `str | dict` — The metadata from the rentry API.

        #### Updates
        - This metadata object with the decoded values.
        """

        try:
            data_json: dict[str, Any] = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError:
            raise RentryInvalidMetadataError("The provided data for building the metadata is not valid JSON.")

        for key, val in data_json.items():
            attr: str = f"_{key}"
            typ: str = self._get_type(key)

            if not hasattr(self, attr):
                continue

            if typ == "bool":
                setattr(self, attr, True if val == "true" else False if val == "false" else bool(val))
            elif typ == "list":
                setattr(self, attr, str(val).split(" "))
            else:
                setattr(self, attr, str(val))

        self.validate()

    @staticmethod
    def build(data: str | dict[str, Any]) -> RentryPageMetadata:
        try:
            data_json: dict[str, Any] = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError:
            raise RentryInvalidMetadataError("The provided data for building the metadata is not valid JSON.")

        metadata = RentryPageMetadata()
        metadata.decode(data_json)

        return metadata

    def __bool__(self) -> bool:
        return any(val is not None for key, val in self.__dict__.items() if key.startswith("_"))

    def __str__(self) -> str:
        return self.encode()

    def __repr__(self) -> str:
        return f"RentryPageMetadata.build({repr(self.encode())})"

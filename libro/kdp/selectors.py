"""KDP form CSS selectors — centralized for easy updates when Amazon changes layout."""

# --- Login & Navigation ---
KDP_BASE_URL = "https://kdp.amazon.com"
KDP_BOOKSHELF_URL = "https://kdp.amazon.com/en_US/bookshelf"
KDP_CREATE_PAPERBACK_URL = "https://kdp.amazon.com/en_US/title-setup/paperback/new/details"

# Bookshelf indicator (proves user is logged in)
BOOKSHELF_INDICATOR = "#kp-bookshelf, #library-view, [data-action='bookshelf']"

# Create new title button
CREATE_NEW_BUTTON = "a[href*='title-setup'], button:has-text('Paperback'), a:has-text('+ Paperback')"

# --- Step 1: Book Details ---

# Title & Subtitle
TITLE_INPUT = "#data-print-book-title, input[name='title'], #title-field input"
SUBTITLE_INPUT = "#data-print-book-subtitle, input[name='subtitle'], #subtitle-field input"

# Author
AUTHOR_FIRST_NAME = "#data-print-book-contributors-0-firstName, input[name*='firstName']"
AUTHOR_LAST_NAME = "#data-print-book-contributors-0-lastName, input[name*='lastName']"

# Description
DESCRIPTION_TEXTAREA = "#data-print-book-description textarea, #cke_data-print-book-description iframe, #data-print-book-description-announcer"
DESCRIPTION_IFRAME = "#cke_data-print-book-description iframe"

# Keywords (7 fields)
KEYWORD_INPUT_TEMPLATE = "#data-print-book-keywords-{index}, input[name*='keyword'][data-index='{index}']"

# Categories
CATEGORY_BUTTON = "button:has-text('Set categories'), a:has-text('Set categories'), #category-chooser-button"

# Language
LANGUAGE_SELECT = "#data-print-book-language, select[name*='language']"

# Publishing rights
RIGHTS_OWN = "#data-print-book-publishing-rights-own, input[value='OWN_COPYRIGHT']"

# Adult content
ADULT_CONTENT_NO = "#data-print-book-is-adult-content-no, input[name*='adultContent'][value='false']"

# Save and Continue (Step 1)
SAVE_CONTINUE_1 = "#save-and-continue-announce, button:has-text('Save and Continue')"

# --- Step 2: Content ---

# Manuscript upload
MANUSCRIPT_UPLOAD = "#data-print-book-publisher-interior-file-upload-browse-button, input[type='file'][accept*='pdf']"
MANUSCRIPT_UPLOAD_INPUT = "input[type='file'][name*='interior'], input[type='file'][accept*='.pdf']"

# Cover upload
COVER_UPLOAD_TAB = "#data-print-book-publisher-cover-choice-file, input[value='UPLOAD']"
COVER_UPLOAD_INPUT = "input[type='file'][name*='cover'], input[type='file'][accept*='image']"

# Trim size
TRIM_SIZE_SELECT = "#data-print-book-publisher-interior-trim-size-select, select[name*='trimSize']"

# Paper type
PAPER_WHITE = "#data-print-book-publisher-interior-media-type-CREME, input[value='WHITE']"
PAPER_CREAM = "#data-print-book-publisher-interior-media-type-WHITE, input[value='CREME']"

# Bleed
NO_BLEED = "#data-print-book-publisher-interior-bleed-type-NO_BLEED, input[value='NO_BLEED']"

# Cover finish
MATTE_FINISH = "#data-print-book-publisher-cover-finish-MATTE, input[value='MATTE']"
GLOSSY_FINISH = "#data-print-book-publisher-cover-finish-GLOSSY, input[value='GLOSSY']"

# Save and Continue (Step 2)
SAVE_CONTINUE_2 = "#save-and-continue-announce, button:has-text('Save and Continue')"

# --- Step 3: Pricing ---

# Marketplace selector
MARKETPLACE_COM = "#data-print-book-pricing-marketplace-US, [data-marketplace='US']"

# Price input
PRICE_INPUT = "#data-print-book-pricing-price-US, input[name*='price'][data-marketplace='US']"

# Publish button (we DON'T click this — user does)
PUBLISH_BUTTON = "#publish-announce, button:has-text('Publish Your Paperback')"

# --- Common ---

# Loading/processing indicators
LOADING_SPINNER = ".a-spinner, .loading-overlay, [class*='spinner']"

# Success/error messages
SUCCESS_MESSAGE = ".a-alert-success, [class*='success']"
ERROR_MESSAGE = ".a-alert-error, [class*='error-message']"

# File upload progress
UPLOAD_PROGRESS = ".upload-progress, [class*='progress']"
UPLOAD_COMPLETE = ".upload-complete, [class*='upload-success'], [class*='file-uploaded']"

from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo,
    FixedFileInfo,
    StringFileInfo,
    StringTable,
    StringStruct,
    VarFileInfo,
    VarStruct,
)

from app_metadata import (
    APP_COMPANY_NAME,
    APP_PRODUCT_NAME,
    APP_VERSION_STRING,
    APP_VERSION_TUPLE,
)


def build_version_info(file_description, internal_name, original_filename):
    return VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=APP_VERSION_TUPLE,
            prodvers=APP_VERSION_TUPLE,
            mask=0x3F,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",
                        [
                            StringStruct("CompanyName", APP_COMPANY_NAME),
                            StringStruct("FileDescription", file_description),
                            StringStruct("FileVersion", APP_VERSION_STRING),
                            StringStruct("InternalName", internal_name),
                            StringStruct("OriginalFilename", original_filename),
                            StringStruct("ProductName", APP_PRODUCT_NAME),
                            StringStruct("ProductVersion", APP_VERSION_STRING),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )

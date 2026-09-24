import os

from scripts.gdal.gdal_commands import get_build_vrt_command
from scripts.gdal.gdal_helper import gdal_info, run_gdal


def main() -> None:
    print(os.environ)
    # gdal_info = subprocess.run(
    #     ["gdalinfo", "/vsis3/nz-elevation/new-zealand/new-zealand/dem_1m/2193/BM35.tiff"], capture_output=True, check=True
    # )
    run_gdal(
        command=get_build_vrt_command(
            files=["/vsis3/nz-elevation/new-zealand/new-zealand/dem_1m/2193/BM35.tiff"], output="/tmp/my.vrt"
        )
    )
    gdalinfo = gdal_info("/tmp/my.vrt")
    print(gdalinfo)


if __name__ == "__main__":
    main()

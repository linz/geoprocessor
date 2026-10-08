import argparse
from datetime import datetime, timezone

from geoprocessor_common.cli.cli_helper import coalesce_multi_single, empty_str_to_false, str_to_bool, str_to_gsd
from geoprocessor_common.cli.common_args import CommonArgumentParser
from geoprocessor_common.data_type import DataType
from geoprocessor_common.datetimes import RFC_3339_DATETIME_FORMAT
from geoprocessor_stac.imagery.collection_context import CollectionContext
from geoprocessor_stac.imagery.constants import DATA_CATEGORIES, DATA_DOMAINS, HUMAN_READABLE_REGIONS, LAND
from geoprocessor_stac.imagery.create_collection_from_items import create_collection_from_items


def get_args_parser() -> CommonArgumentParser:
    parser = CommonArgumentParser(
        description=(
            "Create a STAC Collection from existing STAC Items in a given S3 URI. "
            "Generate a capture-area file if footprint files are present."
        )
    )
    parser.add_argument("--uri", dest="uri", help="s3 path to items and collection.json write location", required=True)
    parser.add_argument("--collection-id", dest="collection_id", help="Collection ID", required=True)
    parser.add_argument(
        "--odr-url",
        dest="odr_url",
        help="The path of the published dataset. Example: 's3://nz-imagery/wellington/porirua_2024_0.1m/rgb/2193/'",
        required=False,
    )
    parser.add_argument(
        "--category",
        dest="category",
        help="Dataset category",
        required=True,
        choices=DATA_CATEGORIES.keys(),
    )
    parser.add_argument(
        "--domain",
        dest="domain",
        help="Dataset domain",
        default=LAND,
        choices=DATA_DOMAINS.keys(),
    )
    parser.add_argument(
        "--region",
        dest="region",
        help="Region of Dataset",
        required=True,
        choices=HUMAN_READABLE_REGIONS.keys(),
    )
    parser.add_argument("--gsd", dest="gsd", help="GSD of imagery Dataset, for example 0.3", type=str_to_gsd, required=True)
    parser.add_argument(
        "--data-type",
        dest="data_type",
        help="Dataset data type",
        choices=[dt.value for dt in DataType],
        type=str,
        required=True,
    )
    parser.add_argument(
        "--geographic-description",
        dest="geographic_description",
        help="Optional Geographic Description of dataset, e.g. Hutt City",
        type=str,
        required=False,
    )
    parser.add_argument("--event", dest="event", help="Event name if applicable", type=str, required=False)
    parser.add_argument(
        "--historic-survey-number",
        dest="historic_survey_number",
        help="Historic Survey Number if Applicable. E.g. SCN8844",
        type=str,
        required=False,
    )
    parser.add_argument(
        "--lifecycle",
        dest="lifecycle",
        help="Designating dataset status",
        required=True,
        choices=["under development", "preview", "ongoing", "completed", "deprecated"],
    )
    parser.add_argument(
        "--linz-slug",
        dest="linz_slug",
        help="linz:slug attribute for this dataset. E.g. bay-of-plenty_2018-2019_0.1m",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--producer",
        dest="producer",
        help="Imagery producer. Ignored if --producer-list passed with a semicolon delimited list.",
    )
    parser.add_argument("--producer-list", dest="producer_list", help="Semicolon delimited list of imagery producers")
    parser.add_argument(
        "--licensor",
        dest="licensor",
        help="Imagery licensor. Ignored if --licensor-list passed with a semicolon delimited list.",
    )
    parser.add_argument("--licensor-list", dest="licensor_list", help="Semicolon delimited list of imagery licensors")
    parser.add_argument(
        "--concurrency", dest="concurrency", help="The number of files to limit concurrent reads", required=True, type=int
    )
    parser.add_argument(
        "--add-title-suffix",
        dest="add_title_suffix",
        help="Add a title suffix to the Collection title based on the lifecycle. For example, '[TITLE] - Preview'",
        type=str_to_bool,
        required=False,
    )
    parser.add_argument(
        "--keep-description",
        dest="keep_description",
        help="Keep the description of the existing Collection as is.",
        type=str_to_bool,
        required=False,
    )
    parser.add_argument(
        "--keep-title",
        dest="keep_title",
        help="Keep the title of the existing Collection as is.",
        type=str_to_bool,
        required=False,
    )
    parser.add_argument(
        "--delete-all-existing-items",
        dest="delete_all_existing_items",
        help="Delete all existing Items in the collection before adding new Items. "
        "To use in the case of re-creating an existing dataset.",
        type=str_to_bool,
        required=False,
    )
    parser.add_argument(
        "--current-datetime",
        dest="current_datetime",
        help=(
            "The datetime to be used as current datetime in the metadata. "
            "Format: RFC 3339 UTC datetime, `YYYY-MM-DDThh:mm:ssZ`."
        ),
        required=False,
        default=datetime.now(timezone.utc).strftime(RFC_3339_DATETIME_FORMAT),
    )
    capture_area_arguments = parser.add_mutually_exclusive_group()
    capture_area_arguments.add_argument(
        "--supplied-capture-area",
        dest="supplied_capture_area",
        help="S3 path to optional externally supplied EPSG:4326 capture area",
        required=False,
        default=False,
        const=False,
        nargs="?",
        type=empty_str_to_false,
    )
    capture_area_arguments.add_argument(
        "--simplified-capture-area",
        dest="simplified_capture_area",
        help="Whether the individual item footprints have been simplified.",
        required=False,
        default=False,
        type=str_to_bool,
    )
    capture_area_arguments.add_argument(
        "--capture-dates",
        dest="capture_dates",
        help="Add a capture-dates.geojson.gz file to the Collection assets",
        required=False,
        default=False,
        type=str_to_bool,
    )

    return parser


def main(args: list[str] | None = None) -> None:
    arguments = get_args_parser().parse_args(args)
    uri = arguments.uri

    if not uri.startswith("s3://"):
        msg = f"uri is not a s3 path: {uri}"
        raise argparse.ArgumentTypeError(msg)

    collection_context = CollectionContext(
        category=arguments.category,
        domain=arguments.domain,
        region=arguments.region,
        gsd=arguments.gsd,
        data_type=DataType(arguments.data_type),
        lifecycle=arguments.lifecycle,
        linz_slug=arguments.linz_slug,
        collection_id=arguments.collection_id,
        geographic_description=arguments.geographic_description,
        event_name=arguments.event,
        historic_survey_number=arguments.historic_survey_number,
        producers=coalesce_multi_single(arguments.producer_list, arguments.producer),
        licensors=coalesce_multi_single(arguments.licensor_list, arguments.licensor),
        add_title_suffix=arguments.add_title_suffix,
        add_capture_dates=arguments.capture_dates,
        delete_existing_items=arguments.delete_all_existing_items,
        keep_description=arguments.keep_description,
        keep_title=arguments.keep_title,
    )

    create_collection_from_items(
        collection_context=collection_context,
        uri=uri,
        concurrency=arguments.concurrency,
        current_datetime=arguments.current_datetime,
        odr_url=arguments.odr_url,
        supplied_capture_area=arguments.supplied_capture_area or None,
        simplified_capture_area=arguments.simplified_capture_area,
    )


if __name__ == "__main__":
    main()

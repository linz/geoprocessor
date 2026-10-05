from dataclasses import dataclass, field
from decimal import Decimal

from geoprocessor_common.data_type import DataType
from geoprocessor_stac.imagery.provider import Provider, ProviderRole, merge_provider_roles


@dataclass
class CollectionContext:  # pylint:disable=too-many-instance-attributes
    """
    Holds contextual data and options used to create or update a STAC Collection.

    This class acts as a structured container for user-provided metadata when
    initializing an `ImageryCollection`. It does not represent a full STAC
    Collection but provides necessary information to generate one.
    It is used to generate titles and descriptions for datasets based on their metadata.
    It also provides a method to get the providers associated with the dataset.


    Attributes:
        category (str): The category of the dataset (e.g., "satellite-imagery").
        domain (str): The domain of the dataset (e.g., "land").
        region (str): The region of the dataset (e.g., "auckland").
        gsd (Decimal): Ground Sample Distance in meters.
        data_type (DataType): The data type of the dataset (e.g., `DataType.UINT8`, `DataType.UINT16`).
        lifecycle (str): Lifecycle status of the dataset (e.g., "completed").
        linz_slug (str): LINZ slug for the dataset.
        producers (list[str]): List of producers for the dataset.
        licensors (list[str]): List of licensors for the dataset.
        collection_id (str | None): Collection ID, if applicable.
        geographic_description (str | None): Geographic description of the dataset.
        event_name (str | None): Event name, if applicable.
        historic_survey_number (str | None): Historic survey number, if applicable.
        add_title_suffix (bool): Whether to add a suffix based on lifecycle status.
        keep_description (bool): Whether to keep the original description.
        keep_title (bool): Whether to keep the original title.
        add_capture_dates (bool): Whether to link the capture dates file to the Collection.
        delete_existing_items (bool): Whether to delete existing items in the collection.
    """

    category: str
    domain: str
    region: str
    gsd: Decimal
    data_type: DataType
    lifecycle: str
    linz_slug: str
    producers: list[str] = field(default_factory=list)
    licensors: list[str] = field(default_factory=list)
    collection_id: str | None = None
    geographic_description: str | None = None
    event_name: str | None = None
    historic_survey_number: str | None = None
    add_title_suffix: bool = True
    keep_description: bool = False
    keep_title: bool = False
    add_capture_dates: bool = False
    delete_existing_items: bool = False

    @property
    def providers(self) -> list[Provider]:
        providers: list[Provider] = [
            {"name": "Toitū Te Whenua Land Information New Zealand", "roles": [ProviderRole.HOST, ProviderRole.PROCESSOR]}
        ]

        for producer_name in self.producers:
            providers.append({"name": producer_name, "roles": [ProviderRole.PRODUCER]})
        for licensor_name in self.licensors:
            providers.append({"name": licensor_name, "roles": [ProviderRole.LICENSOR]})
        return merge_provider_roles(providers)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql.expression import insert
from sqlalchemy import insert

from api.models import Bird, InferenceResult, ServiceCall

BIRD_DICT = {"Grus grus": 1, "Haematopus ostralegus": 2, "Anthus trivialis": 3, "Turdus iliacus": 4, "Turdus philomelos": 5, "Strix aluco": 6, "Motacilla flava": 7, "Vanellus vanellus": 8, "Ficedula hypoleuca": 9, "Erithacus rubecula": 10, "Emberiza hortulana": 11, "Gallinula chloropus": 12, "Alauda arvensis": 14, "Actitis hypoleucos": 15, "Muscicapa striata": 16, "Anas platyrhynchos": 17, "Burhinus oedicnemus": 18, "Fulica atra": 19, "Turdus merula": 20, "Branta bernicla": 21, "Pluvialis apricaria": 22, "Branta canadensis": 23, "Athene noctua": 24, "Tachybaptus ruficollis": 25, "Chroicocephalus ridibundus": 26, "Ardea cinerea": 27, "Corvus corone": 28, "Charadrius hiaticula": 29, "Numenius phaeopus": 30, "Charadrius morinellus": 31, "Calidris alpina": 32, "Coturnix coturnix": 34, "Tyto alba": 35, "Anthus pratensis": 36, "Otus scops": 37, "Tringa ochropus": 38, "Phasianus colchicus": 39, "Tringa totanus": 40, "Tringa nebularia": 41, "Fringilla coelebs": 42, "Gallinago gallinago": 43, "Anser anser": 44, "Melanitta nigra": 45, "Rallus aquaticus": 46, "Anas crecca": 47, "Pica pica": 48, "Nycticorax nycticorax": 49, "Charadrius dubius": 50, "Motacilla alba": 51, "Oriolus oriolus": 52, "Certhia brachydactyla": 53, "Turdus torquatus": 54, "Sitta europaea": 55, "Regulus regulus": 56, "Emberiza citrinella": 57, "Passer domesticus": 58, "Asio otus": 59, "Parus major": 60, "Emberiza schoeniclus": 61, "Phylloscopus collybita": 62, "Sylvia atricapilla": 63, "Coccothraustes coccothraustes": 64, "Turdus pilaris": 65, "Pernis apivorus": 66, "Numenius arquata": 67, "Fringilla montifringilla": 33, "Limosa limosa": 68, "Spinus spinus": 69, "Carduelis carduelis": 70, "Larus fuscus": 71, "Larus argentatus": 72, "Larus michahellis": 73, "Calidris alba": 74, "Chloris chloris": 75, "Anthus campestris": 76, "Anthus cervinus": 77, "Anas acuta": 78, "Lullula arborea": 79, "Botaurus stellaris": 80, "Ixobrychus minutus": 81, "Tringa glareola": 82, "Recurvirostra avosetta": 83, "Cuculus canorus": 84, "Caprimulgus europaeus": 85, "Apus apus": 86, "Porzana porzana": 87, "Egretta garzetta": 88, "Limosa lapponica": 89, "Calidris canutus": 90, "Calidris minuta": 91, "Branta leucopsis": 92, "Emberiza calandra": 93, "Mareca penelope": 94, "Coloeus monedula": 95, "Clamator glandarius": 96, "Himantopus himantopus": 97, "Larus canus": 98, "Turdus viscivorus": 99, "Ardea purpurea": 100, "Porzana pusilla": 101, "Ichthyaetus melanocephalus": 102, "Anser albifrons": 103, "Pluvialis squatarola": 104, "Spatula querquedula": 105, "Sterna hirundo": 106, "Thalasseus sandvicensis": 107, "Hydroprogne caspia": 108, "Arenaria interpres": 109, "Loxia curvirostra": 110, "Spatula clypeata": 111, "Mareca strepera": 112, "Tringa erythropus": 113, "Calidris ferruginea": 114, "Calidris temminckii": 115, "Plectrophenax nivalis": 116, "Calcarius lapponicus": 117, "Emberiza pusilla": 118, "Tringa stagnatilis": 119, "Acanthis cabaret": 120, "Phoenicopterus roseus": 121, "Chlidonias niger": 122, "Chlidonias hybrida": 123, "Tadorna tadorna": 124, "Anthus spinoletta": 125, "Linaria cannabina": 126, "Serinus serinus": 127, "Pyrrhula pyrrhula": 128, "Aegolius funereus": 129, "Glaucidium passerinum": 130, "Bubo bubo": 131, "Luscinia megarhynchos": 13, "Other": 132, "Cettia cetti": 133, "Regulus ignicapilla": 134, "Corvus frugilegus": 135, "Anthus hodgsoni": 136, "Cyanistes caeruleus": 137, "Prunella modularis": 138, "Garrulus glandarius": 139, "Troglodytes troglodytes": 140, "Sturnus vulgaris": 141, "Aegithalos caudatus": 142, "Lophophanes cristatus": 143, "Dendrocopos major": 144, "Non bird sound": 0, "Motacilla cinerea": 145}  # noqa: E501


async def populate_bird_table(session: AsyncSession):
    for bird_name, bird_id in BIRD_DICT.items():
        # Check if the bird already exists in the database
        select_stmt = select(Bird).where(Bird.id == bird_id)
        result = await session.execute(select_stmt)
        bird = result.scalar_one_or_none()

        # If the bird does not exist, insert it
        if bird is None:
            insert_stmt = insert(Bird).values(id=bird_id, name=bird_name)
            await session.execute(insert_stmt)

    # Commit the transaction
    await session.commit()
    

async def create_service_call(
    session: AsyncSession, email: str, ticket_number: str, audio_path: str
):
    service_call = ServiceCall(
        email=email, ticket_number=ticket_number, audio_path=audio_path
    )
    session.add(service_call)
    await session.commit()
    await session.refresh(service_call)
    return service_call

async def create_inference_result(
    session: AsyncSession, 
    service_call_id: int, 
    annotation_path: str, 
    spectrogram_path: str, 
    classification_score: float | None
):
    inference_result = InferenceResult(
        service_call_id=service_call_id,
        annotation_path=annotation_path,
        spectrogram_path=spectrogram_path,
        classification_score=classification_score
    )
    session.add(inference_result)
    await session.commit()
    await session.refresh(inference_result)
    return inference_result
import logging, time
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")
logging.getLogger("src.services.eod_picker_service").setLevel(logging.DEBUG)
from src.services import eod_picker_service as svc

pts, pc, name = svc._fetch_intraday_trends('603019')
print(f"trends single: pts={len(pts)} preClose={pc} name={name} strength={svc.compute_strength_trends(pts) if pts else '-'}")

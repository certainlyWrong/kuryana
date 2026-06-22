MYDRAMALIST_WEBSITE = "https://mydramalist.com/"  # MyDramaList.com


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", reload=True)

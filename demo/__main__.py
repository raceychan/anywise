import uvicorn

app_str = "demo.api:app_factory"
uvicorn.run(app_str, reload=True)

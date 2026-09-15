"""后端启动入口"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("cit_api.main:app", host="0.0.0.0", port=8001, reload=True)

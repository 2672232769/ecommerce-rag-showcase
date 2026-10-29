"""
知识库管理 API（仅管理员可访问）
功能：文档上传、列表查看、删除
性能优化：异步文档处理 + 上传后自动清空缓存
"""
import os
import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..schemas import KnowledgeDocResponse, KnowledgeReprocessResponse
from ..models import User, KnowledgeDocument
from ..database import get_db
from ..auth import get_admin_user
from ..rag import process_document, delete_document_chunks
from ..config import settings

router = APIRouter()

SUPPORTED_TYPES = {".txt", ".md", ".pdf", ".csv"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=KnowledgeDocResponse, summary="上传文档")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """上传知识库文档（仅管理员）"""
    filename = file.filename or ""
    if not filename or filename in {".", ".."} or any(c in filename for c in '/\\:<>"|?*'):
        raise HTTPException(status_code=400, detail="文件名无效，请使用普通文件名。")
    # 校验文件类型
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {ext}，支持: {list(SUPPORTED_TYPES)}",
        )

    # 校验文件大小
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件过大，上限 {MAX_FILE_SIZE // 1024 // 1024} MB",
        )

    if not settings.embedding_configured:
        raise HTTPException(status_code=503, detail="Embedding 接口尚未配置，请填写 backend/.env 后重启服务。")

    # 创建数据库记录
    doc = KnowledgeDocument(
        filename=filename,
        file_type=ext,
        file_size=len(content),
        chunk_count=0,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 每条文档使用独立目录，同名文件不会互相覆盖。
    file_path = Path(settings.upload_dir) / str(doc.id) / filename
    # 使用线程池处理；本次 HTTP 请求会等待入库结束才返回成功。
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(file_path.write_bytes, content)
        chunk_count = await process_document(str(file_path), filename, doc.id)
        doc.chunk_count = chunk_count
        await db.commit()
    except Exception:
        # 回滚本次未完成的入库；清理失败保留错误提示，不返回假成功。
        try:
            await delete_document_chunks(doc.id)
        except Exception:
            logging.getLogger(__name__).warning("失败上传的向量清理未完成: doc_id=%s", doc.id)
        if file_path.exists():
            file_path.unlink()
        # 处理失败，删除记录
        await db.delete(doc)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文档处理失败，请检查文件内容、Embedding 接口、模型和网络。",
        )

    await db.refresh(doc)
    return KnowledgeDocResponse.model_validate(doc)


@router.get("/documents", response_model=list[KnowledgeDocResponse], summary="文档列表")
async def list_documents(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有知识库文档列表（仅管理员）"""
    result = await db.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.uploaded_at.desc())
    )
    docs = result.scalars().all()
    return [KnowledgeDocResponse.model_validate(d) for d in docs]


@router.delete("/documents/{doc_id}", summary="删除文档")
async def delete_document(
    doc_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除知识库文档及其向量数据（仅管理员）"""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # 删除向量库中的文档
    await delete_document_chunks(doc_id)

    # 删除上传的原始文件
    upload_root = Path(settings.upload_dir).resolve()
    file_path = (upload_root / str(doc_id) / doc.filename).resolve()
    if not file_path.is_relative_to(upload_root / str(doc_id)):
        raise HTTPException(status_code=400, detail="存储文件路径无效")
    if file_path.exists():
        file_path.unlink()

    # 删除数据库记录
    await db.delete(doc)
    await db.commit()

    return {"message": f"文档 '{doc.filename}' 已删除"}

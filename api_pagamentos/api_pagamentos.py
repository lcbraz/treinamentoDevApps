import logging
import logging.config
from datetime import datetime
from typing import List
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
import yaml
from fastapi import FastAPI, HTTPException

from database import engine_auto, text, SQLAlchemyError, OperationalError, NoResultFound


# TDDO Adicionar contexto
f = open('logging.yaml', 'r')
d = yaml.safe_load(f)
f.close()
logging.config.dictConfig(d)
logger = logging.getLogger('app')

app = FastAPI()


################
# API usuarios #
################

class Pagamento(BaseModel):
    id: str
    data_pag: datetime
    valor: int

class PagamentoNovo(BaseModel):
    usuario_id: str
    valor: int

class ExcResponse(BaseModel):
    detail: str


@app.get("/api/pagamento/{pag_id}",
         responses={404: {"model": ExcResponse}})
def get_conexao(pag_id) -> Pagamento:
    try:
        with engine_auto.connect() as conn:
            sql = text("SELECT id, data_pag, valor FROM pagamentos WHERE id = :pag_id").\
                    bindparams(pag_id=pag_id)
            result = conn.execute(sql)
            return Pagamento(**dict(zip(result.keys(), result.one())))
    except NoResultFound:
        error_msg = f"Pagamento não encontrada: {pag_id}"
        logger.info(error_msg)
        raise HTTPException(status_code=404, detail=error_msg)
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/api/pagamentos/{usuario_id}")
def list_pagamentos(usuario_id) -> List[Pagamento]:
    pagamentos = []
    try:
        with engine_auto.connect() as conn:
            sql = text("SELECT id, data_pag, valor FROM pagamentos WHERE usuario_id = :usuario_id").\
                    bindparams(usuario_id=usuario_id)
            result = conn.execute(sql)
            for row in result.all():
                pagamentos.append(dict(list(zip(result.keys(), row))))
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))
    else:
        for row in result.all():
            pagamentos.append(dict(list(zip(result.keys(), row))))
    return pagamentos


@app.post("/api/pagamento",
          responses={400: {"model": ExcResponse}})
def create_conexao(pag_novo: PagamentoNovo) -> Pagamento:
    try:
        with engine_auto.connect() as conn:
            sql = text("INSERT INTO pagamentos (usuario_id, valor) VALUES (:usuario_id, :valor) \
                    RETURNING id, data_pag, valor").\
                    bindparams(**pag_novo.model_dump())
            result = conn.execute(sql)
            return Pagamento(**dict(zip(result.keys(), result.one())))
    except IntegrityError as error:
        logger.info(error)
        raise HTTPException(status_code=400, detail=f"Falha ao criar pagamento: {pag_novo}")
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))


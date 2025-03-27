import base64
import logging
import logging.config
from datetime import datetime
from typing import Annotated, List
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
import yaml
from fastapi import Depends, FastAPI, HTTPException, status

from database import engine_auto, text, SQLAlchemyError, OperationalError, NoResultFound


# TDDO Adicionar contexto
f = open('logging.yaml', 'r')
d = yaml.safe_load(f)
f.close()
logging.config.dictConfig(d)
logger = logging.getLogger('app')

app = FastAPI()


##################
# API pagamentos #
##################

class Pagamento(BaseModel):
    id: str
    data_pag: datetime
    valor: int

class PagamentoNovo(BaseModel):
    usuario_id: str
    valor: int

class ExcResponse(BaseModel):
    detail: str



###################################
# Autenticação                    #
# ATENÇÂO: isso não tem segurança #
# não usar me produção            #
###################################

authdb = {'ZGV2b3BzRDNza1QwcA==': 'devops'}
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def fake_decode_token(token: str):
    if token in authdb.keys():
        return authdb[token]

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    hash_check = base64.b64encode(bytes(form_data.username + form_data.password, 'utf-8')).decode('utf-8')
    if hash_check in authdb.keys():
        access_token = hash_check
    else:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    return {"access_token": access_token, "token_type": "bearer"}

###################################


@app.get("/pagamento/{pag_id}",
         responses={404: {"model": ExcResponse}})
def get_pagamentos(pag_id, _: Annotated[str, Depends(get_current_user)]) -> Pagamento:
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


@app.get("/pagamentos/{usuario_id}")
def list_pagamentos(usuario_id, _: Annotated[str, Depends(get_current_user)]) -> List[Pagamento]:
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


@app.post("/pagamento",
          responses={400: {"model": ExcResponse}})
def create_pagamento(pag_novo: PagamentoNovo, _: Annotated[str, Depends(get_current_user)]) -> Pagamento:
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


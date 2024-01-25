import logging
import logging.config
from datetime import datetime
from typing import List, Tuple
from pydantic import BaseModel, TypeAdapter
import yaml
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

from database import engine_auto, engine, text, SQLAlchemyError, OperationalError, NoResultFound

# auth api pagamentos
headers = {"Authorization": "Bearer ZGV2b3BzRDNza1QwcA=="}


# TDDO Adicionar contexto
f = open('logging.yaml', 'r')
d = yaml.safe_load(f)
f.close()
logging.config.dictConfig(d)
logger = logging.getLogger('app')

app = FastAPI()

app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/webfonts", StaticFiles(directory="webfonts"), name="webfonts")

templates = Jinja2Templates(directory="templates")


# TODO
## importar ao invés de copiar
class Pagamento(BaseModel):
    id: str
    data_pag: datetime
    valor: int

class Conexao(BaseModel):
    id: str
    data_inicio: datetime
    data_fim: datetime | None = None
    bytes: int = 0
####


####################
# Funções de ajuda #
####################

def validar_usuario(nome: str, plano: str) -> Tuple[bool, str]:
    planos = ['200M', '500M', '1G']
    
    if plano not in planos:
        sucesso = False
        error_msg = "plano inválido"
    elif len(nome) < 4:
        sucesso = False
        error_msg = "nome inválido"
    else:
        sucesso = True
        error_msg = ""

    return (sucesso, error_msg)


######################
# Frontend principal #
######################

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html"
    )

#
# Cadastro de usuário: exibição e alteração
#

@app.get("/cadastro/{usuario_id}", response_class=HTMLResponse)
def read_cadastro(usuario_id, request: Request):

    ## Obtendo do dados ##
    try:
        with engine_auto.connect() as conn:
            sql = text("SELECT id, nome, data_cadastro, plano FROM usuarios WHERE id = :usuario_id").\
                    bindparams(usuario_id=usuario_id)
            result = conn.execute(sql)
            usuario = result.one()
    except NoResultFound:
        logger.info(f"Usuário {usuario_id} não encontrado")
        raise HTTPException(status_code=404)
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))

    return templates.TemplateResponse(
        request=request, name="cadastro.html", context={"usuario": usuario}
    )


@app.post("/cadastro/{usuario_id}", response_class=HTMLResponse)
def write_cadastro(usuario_id, request: Request,
                   nome: str = Form(),
                   plano: str = Form(),
                   data_cadastro: str = Form()):

    sucesso, error_msg = validar_usuario(nome, plano)

    if not sucesso:
        # popular dados
        usuario = {"id": usuario_id, "nome": nome, "plano": plano,
                   "data_cadastro": data_cadastro}
        return templates.TemplateResponse(
                request=request, name="cadastro.html",
                context={"usuario": usuario, "salvo": True, "sucesso": sucesso,
                         "error_msg": error_msg})

    
    ## Salvar dados ##
    try:
        with engine.connect() as conn:
            sql = text("UPDATE usuarios SET nome = :nome, plano = :plano WHERE id = :usuario_id").\
                    bindparams(usuario_id=usuario_id, nome=nome, plano=plano)
            conn.execute(sql)
            conn.commit()
            
            sql = text("SELECT id, nome, data_cadastro, plano FROM usuarios WHERE id = :usuario_id").\
                    bindparams(usuario_id=usuario_id)
            result = conn.execute(sql)
            usuario = result.one()
    except NoResultFound:
        logger.info(f"Usuário {usuario_id} não encontrado")
        raise HTTPException(status_code=404)
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))

    return templates.TemplateResponse(
            request=request, name="cadastro.html", context={
                "usuario": usuario, "salvo": True, "sucesso": sucesso}
    )


#
# Cadastro de usuário novo
#

@app.get("/cadastronovo", response_class=HTMLResponse)
def new_cadastro(request: Request):
    return templates.TemplateResponse(request=request, name="cadastro_novo.html",
                                      context={"usuario": {}, "sucesso": True})


@app.post("/cadastronovo", response_class=HTMLResponse)
def write_new_cadastro(request: Request,
                   nome: str = Form(),
                   plano: str = Form()):

    sucesso, error_msg = validar_usuario(nome, plano)

    if not sucesso:
        # popular dados
        usuario = {"nome": nome, "plano": plano}
        return templates.TemplateResponse(
                request=request, name="cadastro_novo.html",
                context={"usuario": usuario, "sucesso": sucesso,
                         "error_msg": error_msg})

    
    ## Salvar dados ##
    try:
        with engine.connect() as conn:
            sql = text("INSERT INTO usuarios (nome, plano) VALUES (:nome, :plano) RETURNING id").\
                    bindparams(nome=nome, plano=plano)
            result = conn.execute(sql)
            usuario_id = result.one()[0]
            conn.commit()

            sql = text("SELECT id, nome, data_cadastro, plano FROM usuarios WHERE id = :usuario_id").\
                    bindparams(usuario_id=usuario_id)
            result = conn.execute(sql)
            usuario = result.one()
    except NoResultFound as error:
        logger.info(f"Erro obtenbdo retorno único da query: {error}")
        raise HTTPException(status_code=404)
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))

    return templates.TemplateResponse(
            request=request, name="cadastro.html", context={
                "usuario": usuario, "salvo": True, "sucesso": sucesso}
    )

@app.post("/cadastroapagar/{usuario_id}", response_class=HTMLResponse)
def delete_cadastro(usuario_id, request: Request):
    try:
        with engine.connect() as conn:
            sql = text("DELETE FROM usuarios WHERE id = :usuario_id").\
                    bindparams(usuario_id=usuario_id)
            conn.execute(sql)
            conn.commit()
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))

    return templates.TemplateResponse(
            request=request, name="cadastro_apagado.html", context={"sucesso": True}
    )


@app.get("/lista", response_class=HTMLResponse)
def read_lista(request: Request):
    usuarios = []

    ## Obtendo do dados ##
    try:
        with engine_auto.connect() as conn:
            sql = text("SELECT id, nome, data_cadastro, plano FROM usuarios")
            result = conn.execute(sql)
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))
    else:
        for row in result.all():
            usuarios.append(dict(list(zip(result.keys(), row))))
    
    return templates.TemplateResponse(
        request=request, name="lista.html", context={"usuarios": usuarios}
    )


@app.get("/listapag/{usuario_id}", response_class=HTMLResponse)
async def list_pagamentos(usuario_id, request: Request):
    pagamentos = [] # Lista zerada por padrão
    sucesso = False # Necessário confirmar a obtenção dos dados
    usuario_nome = "" # evitar "unbound var"

    try:
        ## obtendo dados do usuário e pagamentos ##
        async with httpx.AsyncClient() as client:
            # TODO
            # não roda em parelo (Task?)
            res_usuario = await client.get(f"http://localhost:8000/api/usuario/{usuario_id}")
            res_pags = await client.get(f"http://localhost:8001/api/pagamentos/{usuario_id}",
                                        headers=headers)
            
            if res_usuario.status_code == 200 and res_pags.status_code == 200:
                usuario_nome = TypeAdapter(Usuario).validate_python(res_usuario.json()).nome
                pagamentos = TypeAdapter(List[Pagamento]).validate_python(res_pags.json())
                sucesso = True
    except httpx.HTTPError as error:
        logger.error(error)

    return templates.TemplateResponse(
            request=request, name="lista_pag.html",
            context={"pagamentos": pagamentos, "usuario_nome": usuario_nome,
                     "usuario_id": usuario_id, "sucesso": sucesso}
    )

@app.get("/listacon/{usuario_id}", response_class=HTMLResponse)
async def list_conexoes(usuario_id, request: Request):
    conexoes = [] # Lista zerada por padrão
    sucesso = False # Necessário confirmar a obtenção dos dados
    usuario_nome = "" # evitar "unbound var"

    try:
        ## obtendo dados do usuário e conexções ##
        async with httpx.AsyncClient() as client:
            # TODO
            # não roda em parelo (Task?)
            res_usuario = await client.get(f"http://localhost:8000/api/usuario/{usuario_id}")
            res_cons = await client.get(f"http://localhost:8002/api/conexoes/{usuario_id}")
            
            if res_usuario.status_code == 200 and res_cons.status_code == 200:
                usuario_nome = TypeAdapter(Usuario).validate_python(res_usuario.json()).nome
                conexoes = TypeAdapter(List[Conexao]).validate_python(res_cons.json())
                sucesso = True
    except httpx.HTTPError as error:
        logger.error(error)

    return templates.TemplateResponse(
            request=request, name="lista_con.html",
            context={"conexoes": conexoes, "usuario_nome": usuario_nome,
                     "usuario_id": usuario_id, "sucesso": sucesso}
    )

################
# API usuarios #
################

class Usuario(BaseModel):
    id: str
    nome: str
    plano: str
    data_cadastro: datetime

class UsuarioNovo(BaseModel):
    nome: str
    plano: str

class ExcResponse(BaseModel):
    detail: str


@app.get("/api/usuario/{usuario_id}",
         responses={404: {"model": ExcResponse}})
def get_usuario(usuario_id) -> Usuario:
    try:
        with engine_auto.connect() as conn:
            sql = text("SELECT id, nome, data_cadastro, plano FROM usuarios WHERE id = :usuario_id").\
                    bindparams(usuario_id=usuario_id)
            result = conn.execute(sql)
            return Usuario(**dict(zip(result.keys(), result.one())))
    except NoResultFound:
        logger.info(f"Usuário não encontrado: {usuario_id}")
        raise HTTPException(status_code=404, detail=f"Usuário não encontrado: {usuario_id}")
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/api/usuario",
          responses={400: {"model": ExcResponse}})
def create_usuario(usuario: UsuarioNovo) -> Usuario:
    sucesso, error_msg = validar_usuario(usuario.nome, usuario.plano)
    if not sucesso:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        with engine_auto.connect() as conn:
            sql = text("INSERT INTO usuarios (nome, plano) VALUES (:nome, :plano) \
                    RETURNING id, nome, plano, data_cadastro").\
                    bindparams(**usuario.model_dump())
            result = conn.execute(sql)
            return Usuario(**dict(zip(result.keys(), result.one())))
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))


@app.delete("/api/usuario/{usuario_id}",
            responses={400: {"model": ExcResponse}})
def delete_usuario(usuario_id) -> Usuario:
    try:
        with engine_auto.connect() as conn:
            sql = text("DELETE FROM usuarios WHERE id = :usuario_id \
                    RETURNING id, nome, plano, data_cadastro").\
                    bindparams(usuario_id=usuario_id)
            result = conn.execute(sql)
            return Usuario(**dict(zip(result.keys(), result.one())))
    except NoResultFound:
        error_msg = f"Falha ao apagar usuário: {usuario_id}"
        logger.info(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))


@app.put("/api/usuario",
         responses={400: {"model": ExcResponse}})
def update_usuario(usuario: Usuario) -> Usuario:
    sucesso, error_msg = validar_usuario(usuario.nome, usuario.plano)
    if not sucesso:
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        with engine_auto.connect() as conn:
            sql = text("UPDATE usuarios SET nome = :nome, plano = :plano WHERE id = :usuario_id").\
                    bindparams(usuario_id=usuario.id, nome=usuario.nome, plano=usuario.plano)
            conn.execute(sql)
            return usuario
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))


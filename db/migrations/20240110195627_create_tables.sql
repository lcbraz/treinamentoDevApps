-- migrate:up
CREATE TABLE usuarios (
	id VARCHAR(36) NOT NULL DEFAULT uuid(),
	nome VARCHAR(255) NOT NULL,
	data_cadastro TIMESTAMP NOT NULL DEFAULT now(),
	plano VARCHAR(32) NOT NULL CHECK(plano = '200M' OR plano = '500M' OR plano = '1G'),
	PRIMARY KEY (id)
);

CREATE TABLE pagamentos (
	id VARCHAR(36) NOT NULL DEFAULT uuid(),
	usuario_id VARCHAR(36),
	data_pag TIMESTAMP NOT NULL DEFAULT now(),
	valor INT NOT NULL,
	INDEX usuario_id_idx (usuario_id),
	FOREIGN KEY (usuario_id)
		REFERENCES usuarios(id)
		ON DELETE CASCADE
);

CREATE TABLE conexoes (
	id VARCHAR(36) NOT NULL DEFAULT uuid(),
	usuario_id VARCHAR(36),
	data_inicio TIMESTAMP NOT NULL DEFAULT now(),
	data_fim TIMESTAMP DEFAULT NULL,
	bytes INT NOT NULL DEFAULT 0,
	INDEX usuario_id_idx (usuario_id),
	FOREIGN KEY (usuario_id)
		REFERENCES usuarios(id)
		ON DELETE CASCADE
);

-- migrate:down


--
-- PostgreSQL database dump
--


-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.document_approvers DROP CONSTRAINT IF EXISTS document_approvers_document_id_fkey;
ALTER TABLE IF EXISTS ONLY public.documents DROP CONSTRAINT IF EXISTS documents_pkey;
ALTER TABLE IF EXISTS ONLY public.document_approvers DROP CONSTRAINT IF EXISTS document_approvers_pkey;
ALTER TABLE IF EXISTS ONLY public.diadoc_sync_state DROP CONSTRAINT IF EXISTS diadoc_sync_state_pkey;
ALTER TABLE IF EXISTS public.document_approvers ALTER COLUMN id DROP DEFAULT;
DROP TABLE IF EXISTS public.documents;
DROP SEQUENCE IF EXISTS public.document_approvers_id_seq;
DROP TABLE IF EXISTS public.document_approvers;
DROP TABLE IF EXISTS public.diadoc_sync_state;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: diadoc_sync_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.diadoc_sync_state (
    box_id character varying(128) NOT NULL,
    after_index_key text NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: document_approvers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_approvers (
    id integer NOT NULL,
    document_id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    role character varying(255) NOT NULL,
    approved boolean NOT NULL,
    sort_order integer NOT NULL,
    section character varying(16) DEFAULT 'main'::character varying NOT NULL
);


--
-- Name: document_approvers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_approvers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_approvers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_approvers_id_seq OWNED BY public.document_approvers.id;


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id character varying(36) NOT NULL,
    status character varying(32) NOT NULL,
    document_type character varying(32),
    fund_name text NOT NULL,
    fund_inn character varying(12) NOT NULL,
    counterparty_name text NOT NULL,
    counterparty_inn character varying(12) NOT NULL,
    amount double precision,
    period_from date,
    period_to date,
    description text NOT NULL,
    diadoc_box_id character varying(128),
    diadoc_message_id character varying(64),
    diadoc_entity_id character varying(64),
    bank_client_status character varying(32) NOT NULL,
    pdf_filename text,
    received_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    spec_dep_status character varying(32) DEFAULT 'not_sent'::character varying NOT NULL,
    real_estate_enabled boolean DEFAULT false NOT NULL,
    zpif_name text DEFAULT ''::text NOT NULL,
    payment_date date
);


--
-- Name: document_approvers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_approvers ALTER COLUMN id SET DEFAULT nextval('public.document_approvers_id_seq'::regclass);


--
-- Data for Name: diadoc_sync_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.diadoc_sync_state (box_id, after_index_key, updated_at) FROM stdin;
\.


--
-- Data for Name: document_approvers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.document_approvers (id, document_id, name, role, approved, sort_order, section) FROM stdin;
624	0cfd4660-ecde-4e0d-ab02-a081f649070d	Иванов А.А.	Главный бухгалтер	t	0	main
625	0cfd4660-ecde-4e0d-ab02-a081f649070d	Петров В.В.	Финансовый директор	t	1	main
626	0cfd4660-ecde-4e0d-ab02-a081f649070d	Сидорова Е.Е.	Руководитель бэк-офиса	t	2	main
627	0cfd4660-ecde-4e0d-ab02-a081f649070d	Козлов М.И.	Юрист	t	3	main
628	0cfd4660-ecde-4e0d-ab02-a081f649070d	Новикова Т.С.	Руководитель отдела закупок	t	4	main
629	0cfd4660-ecde-4e0d-ab02-a081f649070d	Фёдоров Н.П.	Заместитель генерального директора	t	5	main
630	0cfd4660-ecde-4e0d-ab02-a081f649070d	Козлов Сергей Петрович	Администратор ТЦ	t	0	extra
631	0cfd4660-ecde-4e0d-ab02-a081f649070d	Морозова Елена Владимировна	Специалист по документам и учёту электроэнергии ТЦ	t	1	extra
728	690456ab-0882-4bfa-8334-da772f3951ce	Иванов А.А.	Главный бухгалтер	t	0	main
729	690456ab-0882-4bfa-8334-da772f3951ce	Петров В.В.	Финансовый директор	t	1	main
730	690456ab-0882-4bfa-8334-da772f3951ce	Сидорова Е.Е.	Руководитель бэк-офиса	t	2	main
731	690456ab-0882-4bfa-8334-da772f3951ce	Козлов М.И.	Юрист	t	3	main
732	690456ab-0882-4bfa-8334-da772f3951ce	Новикова Т.С.	Руководитель отдела закупок	t	4	main
733	690456ab-0882-4bfa-8334-da772f3951ce	Фёдоров Н.П.	Заместитель генерального директора	t	5	main
734	690456ab-0882-4bfa-8334-da772f3951ce	Козлов Сергей Петрович	Администратор ТЦ	t	0	extra
735	690456ab-0882-4bfa-8334-da772f3951ce	Морозова Елена Владимировна	Специалист по документам и учёту электроэнергии ТЦ	t	1	extra
736	d10a187f-7ed0-43b0-bad4-7831149770d4	Иванов А.А.	Главный бухгалтер	f	0	main
737	d10a187f-7ed0-43b0-bad4-7831149770d4	Петров В.В.	Финансовый директор	f	1	main
738	d10a187f-7ed0-43b0-bad4-7831149770d4	Сидорова Е.Е.	Руководитель бэк-офиса	f	2	main
739	d10a187f-7ed0-43b0-bad4-7831149770d4	Козлов М.И.	Юрист	f	3	main
740	d10a187f-7ed0-43b0-bad4-7831149770d4	Новикова Т.С.	Руководитель отдела закупок	f	4	main
741	d10a187f-7ed0-43b0-bad4-7831149770d4	Фёдоров Н.П.	Заместитель генерального директора	f	5	main
742	d10a187f-7ed0-43b0-bad4-7831149770d4	Козлов Сергей Петрович	Администратор ТЦ	f	0	extra
743	d10a187f-7ed0-43b0-bad4-7831149770d4	Морозова Елена Владимировна	Специалист по документам и учёту электроэнергии ТЦ	f	1	extra
648	8890658c-0409-4450-b25f-9fc812639cf4	Иванов А.А.	Главный бухгалтер	f	0	main
649	8890658c-0409-4450-b25f-9fc812639cf4	Петров В.В.	Финансовый директор	f	1	main
650	8890658c-0409-4450-b25f-9fc812639cf4	Сидорова Е.Е.	Руководитель бэк-офиса	f	2	main
651	8890658c-0409-4450-b25f-9fc812639cf4	Козлов М.И.	Юрист	f	3	main
652	8890658c-0409-4450-b25f-9fc812639cf4	Новикова Т.С.	Руководитель отдела закупок	f	4	main
653	8890658c-0409-4450-b25f-9fc812639cf4	Фёдоров Н.П.	Заместитель генерального директора	f	5	main
654	8890658c-0409-4450-b25f-9fc812639cf4	Козлов Сергей Петрович	Администратор ТЦ	f	0	extra
655	8890658c-0409-4450-b25f-9fc812639cf4	Морозова Елена Владимировна	Специалист по документам и учёту электроэнергии ТЦ	f	1	extra
\.


--
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documents (id, status, document_type, fund_name, fund_inn, counterparty_name, counterparty_inn, amount, period_from, period_to, description, diadoc_box_id, diadoc_message_id, diadoc_entity_id, bank_client_status, pdf_filename, received_at, updated_at, spec_dep_status, real_estate_enabled, zpif_name, payment_date) FROM stdin;
8890658c-0409-4450-b25f-9fc812639cf4	new	utd	ООО «ФИРМА 1»		ООО «С-Битрикс»		\N	\N	\N	УПД_со_статусом_1.pdf	\N	\N	\N	paid	/home/clawbot1983/Cursor/Veles/veles/pdf_docs/УПД_со_статусом_1.pdf	2026-06-21 01:44:01.128804+00	2026-06-21 02:41:01.025984+00	not_sent	f		\N
0cfd4660-ecde-4e0d-ab02-a081f649070d	sent_to_avankor	invoice	УК «Весы Управление»	7701000001	ООО «Калейдоскоп»	7714559223	5900	2016-01-20	2026-06-21	Обслуживание орттехники	\N	\N	\N	paid	/home/clawbot1983/Cursor/Veles/veles/pdf_docs/rekomendovannaya_forma_UPD.pdf	2026-06-21 01:44:01.128756+00	2026-06-21 02:18:27.630483+00	sent	t	ЗПИФ «Весы»	2026-06-28
43ed4cbc-abd5-4f20-8938-c17b19c12cd8	new	\N			PDF-1-3		\N	\N	\N	PDF-1-3.pdf	\N	\N	\N	paid	/home/clawbot1983/Cursor/Veles/veles/pdf_docs/PDF-1-3.pdf	2026-06-21 01:44:01.12874+00	2026-06-21 02:21:36.616665+00	not_sent	f		\N
7cfac6ac-a78e-4e00-9c19-427cc19b258b	new	\N			04 07 17 kak vistavit schet obrazets		\N	\N	\N	04_07_17_kak_vistavit_schet_obrazets.pdf	\N	\N	\N	paid	/home/clawbot1983/Cursor/Veles/veles/pdf_docs/04_07_17_kak_vistavit_schet_obrazets.pdf	2026-06-21 01:44:01.128712+00	2026-06-21 02:40:55.730878+00	not_sent	f		\N
690456ab-0882-4bfa-8334-da772f3951ce	sent_to_avankor	invoice	АО «АЛЬФА-БАНК» г. Москва		ООО «ПАЛЛИОМЕД»	7716936820	499500	2025-05-05	2026-06-21	Оплата поставки товаров	\N	\N	\N	paid	/home/clawbot1983/Cursor/Veles/veles/pdf_docs/schet-na-oplatu-№-134-ot-05-maya-2025-g.pdf	2026-06-21 01:44:01.128774+00	2026-06-21 02:43:24.608784+00	sent	f	ЗПИФ «Весы»	2026-06-30
d10a187f-7ed0-43b0-bad4-7831149770d4	on_approval	invoice	УК «Весы Управление»	7701000001	upd-example		0	2026-06-21	2026-06-21	upd-example.pdf	\N	\N	\N	paid	/home/clawbot1983/Cursor/Veles/veles/pdf_docs/upd-example.pdf	2026-06-21 01:44:01.128788+00	2026-06-21 02:43:33.394819+00	not_sent	t	ЗПИФ «Весы»	2026-06-21
\.


--
-- Name: document_approvers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.document_approvers_id_seq', 743, true);


--
-- Name: diadoc_sync_state diadoc_sync_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diadoc_sync_state
    ADD CONSTRAINT diadoc_sync_state_pkey PRIMARY KEY (box_id);


--
-- Name: document_approvers document_approvers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_approvers
    ADD CONSTRAINT document_approvers_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: document_approvers document_approvers_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_approvers
    ADD CONSTRAINT document_approvers_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--



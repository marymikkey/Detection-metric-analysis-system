--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: datasets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.datasets (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(256) NOT NULL,
    path text NOT NULL,
    description text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.datasets OWNER TO postgres;

--
-- Name: eval_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.eval_profiles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(256) NOT NULL,
    params jsonb DEFAULT '{}'::jsonb NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.eval_profiles OWNER TO postgres;

--
-- Name: experiments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.experiments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_config_id uuid,
    model_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    eval_params jsonb,
    status character varying(50) DEFAULT 'pending'::character varying,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    log_file text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.experiments OWNER TO postgres;

--
-- Name: metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.metrics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    experiment_id uuid NOT NULL,
    metric_name character varying(100) NOT NULL,
    metric_value numeric,
    group_type character varying(50),
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.metrics OWNER TO postgres;

--
-- Name: models; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.models (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(256) NOT NULL,
    weights_path text NOT NULL,
    script_path text NOT NULL,
    description text,
    architecture character varying(100),
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.models OWNER TO postgres;

--
-- Name: run_config_datasets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.run_config_datasets (
    run_config_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    "position" integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.run_config_datasets OWNER TO postgres;

--
-- Name: run_config_models; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.run_config_models (
    run_config_id uuid NOT NULL,
    model_id uuid NOT NULL,
    "position" integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.run_config_models OWNER TO postgres;

--
-- Name: run_configs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.run_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(256) NOT NULL,
    eval_profile_id uuid NOT NULL,
    description text,
    single_class boolean DEFAULT false NOT NULL,
    output_md text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.run_configs OWNER TO postgres;

--
-- Name: datasets datasets_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.datasets
    ADD CONSTRAINT datasets_name_key UNIQUE (name);


--
-- Name: datasets datasets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.datasets
    ADD CONSTRAINT datasets_pkey PRIMARY KEY (id);


--
-- Name: eval_profiles eval_profiles_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.eval_profiles
    ADD CONSTRAINT eval_profiles_name_key UNIQUE (name);


--
-- Name: eval_profiles eval_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.eval_profiles
    ADD CONSTRAINT eval_profiles_pkey PRIMARY KEY (id);


--
-- Name: experiments experiments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiments
    ADD CONSTRAINT experiments_pkey PRIMARY KEY (id);


--
-- Name: metrics metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.metrics
    ADD CONSTRAINT metrics_pkey PRIMARY KEY (id);


--
-- Name: models models_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.models
    ADD CONSTRAINT models_name_key UNIQUE (name);


--
-- Name: models models_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.models
    ADD CONSTRAINT models_pkey PRIMARY KEY (id);


--
-- Name: run_config_datasets run_config_datasets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.run_config_datasets
    ADD CONSTRAINT run_config_datasets_pkey PRIMARY KEY (run_config_id, dataset_id);


--
-- Name: run_config_models run_config_models_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.run_config_models
    ADD CONSTRAINT run_config_models_pkey PRIMARY KEY (run_config_id, model_id);


--
-- Name: run_configs run_configs_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.run_configs
    ADD CONSTRAINT run_configs_name_key UNIQUE (name);


--
-- Name: run_configs run_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.run_configs
    ADD CONSTRAINT run_configs_pkey PRIMARY KEY (id);


--
-- Name: idx_experiments_ds; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_experiments_ds ON public.experiments USING btree (dataset_id);


--
-- Name: idx_experiments_model; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_experiments_model ON public.experiments USING btree (model_id);


--
-- Name: idx_experiments_run; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_experiments_run ON public.experiments USING btree (run_config_id);


--
-- Name: idx_metrics_experiment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_metrics_experiment ON public.metrics USING btree (experiment_id);


--
-- Name: idx_metrics_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_metrics_group ON public.metrics USING btree (group_type);


--
-- Name: idx_metrics_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_metrics_name ON public.metrics USING btree (metric_name);


--
-- Name: idx_rcd_dataset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rcd_dataset_id ON public.run_config_datasets USING btree (dataset_id);


--
-- Name: idx_rcd_run_config_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rcd_run_config_id ON public.run_config_datasets USING btree (run_config_id);


--
-- Name: idx_rcm_model_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rcm_model_id ON public.run_config_models USING btree (model_id);


--
-- Name: idx_rcm_run_config_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rcm_run_config_id ON public.run_config_models USING btree (run_config_id);


--
-- Name: datasets trg_datasets_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_datasets_updated_at BEFORE UPDATE ON public.datasets FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: eval_profiles trg_eval_profiles_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_eval_profiles_updated_at BEFORE UPDATE ON public.eval_profiles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: models trg_models_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_models_updated_at BEFORE UPDATE ON public.models FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: run_configs trg_run_configs_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_run_configs_updated_at BEFORE UPDATE ON public.run_configs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: experiments experiments_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiments
    ADD CONSTRAINT experiments_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id) ON DELETE RESTRICT;


--
-- Name: experiments experiments_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiments
    ADD CONSTRAINT experiments_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.models(id) ON DELETE RESTRICT;


--
-- Name: experiments experiments_run_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.experiments
    ADD CONSTRAINT experiments_run_config_id_fkey FOREIGN KEY (run_config_id) REFERENCES public.run_configs(id) ON DELETE SET NULL;


--
-- Name: metrics metrics_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.metrics
    ADD CONSTRAINT metrics_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES public.experiments(id) ON DELETE CASCADE;


--
-- Name: run_config_datasets run_config_datasets_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.run_config_datasets
    ADD CONSTRAINT run_config_datasets_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id) ON DELETE RESTRICT;


--
-- Name: run_config_datasets run_config_datasets_run_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.run_config_datasets
    ADD CONSTRAINT run_config_datasets_run_config_id_fkey FOREIGN KEY (run_config_id) REFERENCES public.run_configs(id) ON DELETE CASCADE;


--
-- Name: run_config_models run_config_models_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.run_config_models
    ADD CONSTRAINT run_config_models_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.models(id) ON DELETE RESTRICT;


--
-- Name: run_config_models run_config_models_run_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.run_config_models
    ADD CONSTRAINT run_config_models_run_config_id_fkey FOREIGN KEY (run_config_id) REFERENCES public.run_configs(id) ON DELETE CASCADE;


--
-- Name: run_configs run_configs_eval_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.run_configs
    ADD CONSTRAINT run_configs_eval_profile_id_fkey FOREIGN KEY (eval_profile_id) REFERENCES public.eval_profiles(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--


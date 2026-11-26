CREATE FUNCTION fn_session_rate_check_public() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM workout_session
                   WHERE id = NEW.id_workout_session AND public) THEN
        RAISE EXCEPTION 'La sesión % no es pública y no se puede valorar', NEW.id_workout_session;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_session_rate_check_public
    BEFORE INSERT OR UPDATE ON session_rate
    FOR EACH ROW EXECUTE FUNCTION fn_session_rate_check_public();

CREATE FUNCTION fn_workout_rate_check_public() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM workout
                   WHERE id = NEW.id_workout AND public AND state) THEN
        RAISE EXCEPTION 'El ejercicio % debe ser público y estar activo para valorarlo', NEW.id_workout;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_workout_rate_check_public
    BEFORE INSERT OR UPDATE ON workout_rate
    FOR EACH ROW EXECUTE FUNCTION fn_workout_rate_check_public();

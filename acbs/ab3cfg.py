import os

from acbs.const import AUTOBUILD_CONF_DIR
from acbs import bashvar
from pyparsing import ParseException # type: ignore


def is_in_stage2() -> bool:
    ab3cfg_path: str = os.path.join(AUTOBUILD_CONF_DIR, 'ab3cfg.sh')
    try:
        with open(ab3cfg_path) as f:
            vars = bashvar.eval_bashvar(f.read(), filename=ab3cfg_path)
            stage2_val: str = vars.get('ABSTAGE2')
            return True if stage2_val == '1' else False
    except OSError as e:
        raise RuntimeError(f'Unable to read Autobuild config file {ab3cfg_path}.') from e
    except ParseException as e:
        raise RuntimeError(f'Error occurred while parsing Autobuild config file {ab3cfg_path}.') from e
    except Exception as e:
        raise RuntimeError(f'Error occurred while checking whether stage 2 mode is enabled.') from e

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/02_export.ipynb.

# %% auto 0
__all__ = ['extract_comments', 'NotebookProcessor', 'ExportModuleProcessor', 'nb_export']

# %% ../nbs/02_export.ipynb 3
from .read import *
from .maker import *
from .imports import *

from fastcore.script import *
from fastcore.imports import *

from collections import defaultdict
from pprint import pformat
from inspect import signature,Parameter
import ast,contextlib,copy

# %% ../nbs/02_export.ipynb 8
def extract_comments(ss):
    "Take leading comments from lines of code in `ss`, remove `#`, and split"
    ss = ss.splitlines()
    first_code = first(i for i,o in enumerate(ss) if not o.strip() or re.match('\s*[^#\s]', o))
    return L((s.strip()[1:]).strip().split() for s in ss[:first_code]).filter()

# %% ../nbs/02_export.ipynb 11
class NotebookProcessor:
    "Base class for nbprocess notebook processors"
    def __init__(self, path, debug=False): self.nb,self.path,self.debug = read_nb(path),Path(path),debug

# %% ../nbs/02_export.ipynb 16
@functools.lru_cache(maxsize=None)
def _param_count(f):
    "Number of parameters accepted by function `f`"
    params = list(signature(f).parameters.values())
    # If there's a `*args` then `f` can take as many params as neede
    if first(params, lambda o: o.kind==Parameter.VAR_POSITIONAL): return 99
    return len([o for o in params if o.kind in (Parameter.POSITIONAL_ONLY,Parameter.POSITIONAL_OR_KEYWORD)])

# %% ../nbs/02_export.ipynb 18
@patch
def process_comment(self:NotebookProcessor, cell_type, comment, idx):
    cmd,*args = comment
    self.comment,self.idx = comment,idx
    cmd = f"{cmd}_{cell_type}"
    if self.debug: print(cmd, args)
    f = getattr(self, cmd, None)
    if not f or _param_count(f)<len(args): return True
    return f(*args)

# %% ../nbs/02_export.ipynb 23
@patch
def process_cell(self:NotebookProcessor, cell):
    comments = extract_comments(cell.source)
    self.cell = cell
    if not comments: return
    keeps = [self.process_comment(cell.cell_type, comment, i)
             for i,comment in enumerate(comments)]
    self.cell.source = ''.join([o for i,o in enumerate(self.cell.source.splitlines(True))
                                if i>=len(keeps) or keeps[i]])

# %% ../nbs/02_export.ipynb 28
@patch
def process(self:NotebookProcessor):
    "Process all cells with `process_cell` and replace `self.nb.cells` with result"
    for i in range_of(self.nb.cells): self.process_cell(self.nb.cells[i])

# %% ../nbs/02_export.ipynb 33
class ExportModuleProcessor(NotebookProcessor):
    "A `NotebookProcessor` which exports code to a module"
    def __init__(self, path, dest, mod_maker=ModuleMaker, debug=False):
        dest = Path(dest)
        store_attr()
        super().__init__(path,debug=debug)

    def process(self):
        self.default_exp,self.modules,self.in_all = None,defaultdict(L),defaultdict(L)
        super().process()

# %% ../nbs/02_export.ipynb 36
@patch
def default_exp_code(self:ExportModuleProcessor, exp_to): self.default_exp = exp_to

# %% ../nbs/02_export.ipynb 39
@patch
def exporti_code(self:ExportModuleProcessor, exp_to=None):
    "Export a cell, without including the definition in `__all__`"
    self.modules[ifnone(exp_to, '#')].append(self.cell)

# %% ../nbs/02_export.ipynb 42
@patch
def export_code(self:ExportModuleProcessor, exp_to=None):
    "Export a cell, adding the definition in `__all__`"
    self.exporti_code(exp_to)
    self.in_all[ifnone(exp_to, '#')].append(self.cell)

# %% ../nbs/02_export.ipynb 44
@patch
def create_modules(self:ExportModuleProcessor):
    "Create module(s) from notebook"
    self.process()
    for mod,cells in self.modules.items():
        all_cells = self.in_all[mod]
        name = self.default_exp if mod=='#' else mod
        mm = self.mod_maker(dest=self.dest, name=name, nb_path=self.path, is_new=mod=='#')
        mm.make(cells, all_cells)

# %% ../nbs/02_export.ipynb 52
def nb_export(nbname, lib_name=None):
    if lib_name is None: lib_name = get_config().lib_name
    ExportModuleProcessor('02_export.ipynb', lib_name).create_modules()

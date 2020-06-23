#include <pybind11/pybind11.h>

int check_available(const char *name);
bool apt_init_system();

PYBIND11_MODULE(miniapt_query, m) {
    m.doc() = "Query if a package exists in the repository";
    m.def("apt_init_system", &apt_init_system, "Initialize system cache");
    m.def("check_if_available", &check_available, "Check if a package exists in the repository");
}

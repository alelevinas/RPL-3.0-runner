#include <criterion/criterion.h>
#include "main.c"

Test(arithmetic, test_add) {
    cr_assert_eq(add(2, 3), 5);
}

Test(arithmetic, test_multiply) {
    cr_assert_eq(multiply(3, 4), 12);
}

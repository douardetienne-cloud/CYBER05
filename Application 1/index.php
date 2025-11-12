<?php
function print_variable($key, $escape = true) {
    if (isset($_GET[$key])) {
        $value = $_GET[$key];
        if ($escape) {
            $value = htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
        }
        echo "Votre variable GET '$key' est : " . $value . "<br>";
    } else {
        echo "La variable GET '$key' n'est pas d\u00e9finie.<br>";
    }
}

print_variable('nom');
print_variable('age', false);
?>

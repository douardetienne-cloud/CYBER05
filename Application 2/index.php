<?php
// Pr\u00e9-remplissage si on revient depuis la page 2
$first = isset($_GET['first']) ? $_GET['first'] : '';
$last  = isset($_GET['last'])  ? $_GET['last']  : '';
?>
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Formulaire et page 2</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; }
    label { display:block; margin: .5rem 0 .25rem; }
    input[type="text"] { padding:.4rem; width: 300px; }
    button { margin-top: 1rem; padding:.5rem 1rem; }
  </style>
</head>
<body>
  <h1>Veuillez entrer vos informations</h1>

  <form action="page2.php" method="get">
    <label for="first">First Name :</label>
    <input type="text" id="first" name="first" value="<?php echo $first; ?>" required>

    <label for="last">Last Name :</label>
    <input type="text" id="last" name="last" value="<?php echo $last; ?>" required>

    <button type="submit">Valider</button>
  </form>
</body>
</html>

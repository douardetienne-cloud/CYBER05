<?php
$first = $_GET['first'] ?? '';
$last  = $_GET['last'] ?? '';

if ($first === '' || $last === '') {
    header('Location: index.php');
    exit;
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Bienvenue</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; }
    h1 { margin-top:0; }
    button { margin-top: 1rem; padding:.5rem 1rem; }
  </style>
</head>
<body>
  <h1>Bienvenue sur ma page web <?php echo $first . ' ' . $last; ?></h1>

  <form action="index.php" method="get">
    <input type="hidden" name="first" value="<?php echo $first; ?>">
    <input type="hidden" name="last"  value="<?php echo $last; ?>">
    <button type="submit">Retour</button>
  </form>
</body>
</html>

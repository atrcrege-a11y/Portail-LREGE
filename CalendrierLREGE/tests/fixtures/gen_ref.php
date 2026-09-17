<?php
/**
 * Génère tests/fixtures/php_reference.json : valeurs de référence produites par
 * LREGE_Texte (extension calendrier-lrege v1.0.1) sur le jeu d'essai commun.
 * Lancer : php gen_ref.php <racine-extension> <classeur.xlsx> > php_reference.json
 */
// $argv[1] : racine de l'extension calendrier-lrege ; $argv[2] : classeur .xlsx.
$ext = isset( $argv[1] ) && '' !== $argv[1] ? rtrim( $argv[1], '/\\' ) : __DIR__;
define('ABSPATH', $ext.'/');
require $ext.'/includes/class-lrege-const.php';
require $ext.'/includes/class-lrege-texte.php';
require $ext.'/includes/class-lrege-xlsx.php';
require $ext.'/includes/class-lrege-classeur.php';

// ── 1. Dates ──────────────────────────────────────────────────────────────
$dates = array(
    // cas de test-tri.php
    '3-4 avril 2027', '3-4 avr. 2027', '26-27 sept. 2026', 'mai 2027',
    '1-2 mai 2027', '30 jan. 2027', '3-4 avr. 2027 ou 1-2 mai 2027',
    '1 août 2027', '3-4 pluviose 2027', 'semaine 12',
    // bornes et formes tordues
    '', '   ', "\xC2\xA0 26-27 sept. 2026 \xC2\xA0", '26 - 27 sept. 2026',
    '26-27 SEPT. 2026', '26-27 Sept 2026', '1 mai 2027', '01 mai 2027',
    'Mai 2027', 'MAI 2027', 'mai. 2027', 'mai 2027 ou juin 2027',
    '2027', '26/09/2026', '26 sept.2026', '26  sept.  2026',
    '31 déc. 2026', '1 janv. 2027', '23 mai 2027', 'juin 2027',
    '6-7 fév. 2027', '6-7 février 2027', '1-2 mai 2027 (à confirmer)',
    'pluviose 2027', '12 germinal 2027', 'du 3 au 4 avril 2027',
);
// les 12 mois, abrégé et nom complet, plus toutes les clés de LREGE_Const::mois()
foreach ( array_keys( LREGE_Const::mois() ) as $mo ) {
    $dates[] = "1 $mo 2027";
    $dates[] = "1 $mo. 2027";
    $dates[] = "$mo 2027";
    $dates[] = "10-11 $mo 2027";
}
$dates = array_values( array_unique( $dates ) );

$out_dates = array();
foreach ( $dates as $d ) {
    $out_dates[] = array(
        'in'        => $d,
        'tri_key'   => LREGE_Texte::tri_key( $d ),
        'illisible' => LREGE_Texte::date_illisible( $d ),
    );
}

// ── 2. Catégories ─────────────────────────────────────────────────────────
$cats = array(
    '', 'Seniors', 'M13 à Seniors', 'M7 à Vétérans', 'Seniors à M13',
    'VET + M13', 'PARA + M13 épée', 'M13 à Seniors + VET', 'M9-M11-M13',
    'M13 a Seniors', 'M13 À Seniors', 'vet + m13', 'PARA', 'Parasport',
    'paras', 'Sén à M20', 'M20 à Sén', 'M13 à pluviose', 'Cadet',
    'Benjamin + Sénior', 'M17 mixte', 'M13 épée + PARA', 'Vétérans',
    'M11 à M15', 'M15', 'M13 + M15 + M17', 'M13+M15', 'Seniors + Vétérans',
    'M13 à M13', 'Toutes catégories', 'M7 à M9 et M13', 'VET',
    'M20 à Vétérans', 'Sabre laser Sénior', 'M13 à Seniors (hors M15)',
);
$out_cats = array();
foreach ( $cats as $c ) {
    $dev = LREGE_Texte::developper( $c );
    $nor = LREGE_Texte::normaliser( $dev );
    $lst = LREGE_Texte::categories( array( $nor ) );
    $out_cats[] = array(
        'in'          => $c,
        'developpe'   => $dev,
        'normalise'   => $nor,
        'cats'        => $lst,
        'cats_index'  => LREGE_Texte::cats_index( $lst ),
    );
}
// cats_index sur des listes déjà constituées (dont l'ordre n'est pas trié ici)
$listes = array(
    array(), array('M13'), array('M13','M15'), array('Parasport','M13'),
    array('Seniors','Vétérans'), array('M7','M9','M11','M13','M15','M17','M20','Seniors','Vétérans'),
);
$out_index = array();
foreach ( $listes as $l ) {
    $out_index[] = array( 'in' => $l, 'cats_index' => LREGE_Texte::cats_index( $l ) );
}

// ── 3. cle_source (avec dédoublonnage) ────────────────────────────────────
// Reproduit la boucle de LREGE_Classeur::finaliser() sur un jeu contenant
// des doublons volontaires. L'ordre d'entrée est celui du tri chronologique.
$brutes = array(
    array('26-27 sept. 2026','Épée','ER1',''),
    array('26-27 sept. 2026','Épée','ER1',''),               // doublon 1
    array('26-27 sept. 2026','Épée','ER1',''),               // doublon 2
    array('21-22 nov. 2026','Coupe de Lorraine','CDL 1','VANDOEUVRE'),
    array('3-4 avr. 2027','Lorraine','Tournoi club','SOIG'),
    array('','','',''),
    array('26-27 sept. 2026','Épée','ER2',''),
    array('3-4 avr. 2027','Lorraine','Tournoi club','SOIG'), // doublon 3
);
$vues = array(); $cles = array(); $dupes = array();
foreach ( $brutes as $b ) {
    $base = $b[0].'|'.$b[1].'|'.$b[2].'|'.$b[3];
    $cle = $base; $n = 1;
    while ( isset( $vues[ $cle ] ) ) { ++$n; $cle = $base.'#'.$n; }
    if ( $n > 1 ) { $dupes[] = $base; }
    $vues[ $cle ] = true; $cles[] = $cle;
}
$out_cle = array(
    'lignes'   => array_map( function ( $b ) {
        return array( 'date_texte'=>$b[0], 'bloc'=>$b[1], 'type'=>$b[2], 'club'=>$b[3] );
    }, $brutes ),
    'attendu'  => $cles,
    'doublons' => $dupes,
);

// ── 4. Le classeur réel 2026-2027 ─────────────────────────────────────────
$classeur = null;
if ( isset( $argv[2] ) && '' !== $argv[2] && file_exists( $argv[2] ) ) {
    $c = new LREGE_Classeur( $argv[2], basename( $argv[2] ) );
    $lignes = array();
    foreach ( $c->lignes as $x ) {
        $lignes[] = array(
            'date_texte'=>$x['date_texte'], 'jours'=>$x['jours'], 'bloc'=>$x['bloc'],
            'type'=>$x['type'], 'categories'=>$x['categories'], 'lieu'=>$x['lieu'],
            'club'=>$x['club'], 'statut'=>$x['statut'], 'est_tournoi'=>$x['est_tournoi'],
            'armes'=>$x['armes'], 'tri_key'=>$x['tri_key'],
            'cle_source'=>$x['cle_source'], 'cats'=>$x['cats'], 'cats_index'=>$x['cats_index'],
        );
    }
    $classeur = array( 'saison'=>$c->saison, 'nb_officiels'=>$c->nb_officiels,
                       'nb_tournois'=>$c->nb_tournois, 'lignes'=>$lignes );
}

echo json_encode( array(
    'source'      => 'calendrier-lrege 1.0.1 — LREGE_Texte / LREGE_Classeur',
    'php'         => PHP_VERSION,
    'dates'       => $out_dates,
    'categories'  => $out_cats,
    'cats_index'  => $out_index,
    'cle_source'  => $out_cle,
    'classeur'    => $classeur,
), JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT ), "\n";

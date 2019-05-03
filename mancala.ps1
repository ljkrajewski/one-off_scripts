#mancala.ps1

$initManacala = @(4,4,4,4,4,4,0,4,4,4,4,4,4,0)
#$initManacala = @(0,0,2,3,2,1,15,5,1,2,3,1,0,13)

### Functions ###

function writehost-array {
  param ( $array )

  Write-Debug "Entering writehost-array"
  if ($array -eq $null) { throw "Null gamestate in writehost-array" }

   for ($i=0; $i -lt $array.count; $i++) {
     write-host -NoNewline "$($array[$i]) "
     if ($i -eq 6) { write-host -NoNewline "++ " }
     elseif (($i -eq 5) -or ($i -eq 12)) { write-host -NoNewline "- " }
   }
  write-host "`tHeuristic: $(calc-heuristic $array.clone())"
  Write-Debug "Exiting writehost-array"
}

function new-gameobject {
  param ( $move, $gamestate, $heuristic )

  new-object PSObject -Property @{
    move=$move;
    gamestate=$gamestate.clone();
    heuristic=$heuristic
  }
}

function test-endgame {
  param ( $gamestate )

  Write-Debug "Entering test-endgame"
  if ($gamestate -eq $null) { throw "Null gamestate in test-endgame" }

  $endgame = $true
  for ($i=0; $i -le 5; $i++) {
    $endgame = $endgame -and ($gamestate[$i] -eq 0)
  }
  if (!($endgame)) {
    $endgame = $true
    for ($i=7; $i -le 12; $i++) {
      $endgame = $endgame -and ($gamestate[$i] -eq 0)
    }
  }
  Write-Debug "Exiting test-endgame"
  $endgame
}

function calc-heuristic {
  param ( [array]$state )

  Write-Debug "Entering calc-heuristic"
  if ($state -eq $null) { throw "Null gamestate in calc-heuristic" }

  if (test-endgame $state) {
    if ($state[6] -gt $state[13]) { $return = 100 }  #Player 1 wins
    elseif ($state[6] -lt $state[13]) { $return = -100 }  #Player 2 wins
    else { $return = 50 }  #Tie
  } else {
    $return = $state[6] - $state[13]
  }
  Write-Debug "Exiting calc-heuristic"
  $return
}

function make-move {
  param ( $player, $selection, $curMancala )

  $mancala = $curMancala.clone()
  $offset = ($player - 1) * 7
  $numMoves = $mancala[$selection+$offset-1]
  $mancala[$selection+$offset-1] = 0
  for ($i=$selection+1; $i -le $selection+$numMoves; $i++) {
    $place = ((($i-1) % 13) + $offset ) % 14
    $mancala[$place]++
  }
  $mancala
}

function user-move {
  param ( $player, $gamestate )

  do {
    [int]$selection = read-host "Player $player (1-6)"
    $validMove = ($selection -ge 1) -and ($selection -le 6) -and ($gamestate[$selection-1] -ne 0)
    if (!($validMove)) {
      write-host -ForegroundColor Yellow "Invalid move -- try again."
    }
  } until ($validMove)
  $(make-move $player $selection $gamestate).clone()
}

function list-moves {
#create array of possible moves

  param ( $player, $currGamestate )

  Write-Debug "Entering list-moves"
  if ($currGamestate -eq $null) { throw "Null gamestate in list-move" }

  $results = New-Object System.Collections.ArrayList
  switch ($player) {
    1 { $multiplier = 1; $offset = 0 }
    2 { $multiplier = -1; $offset = 7 }
  }
  for ($i=1; $i -le 6; $i++) {
    $gamestate = $currGamestate.Clone()
    if ($gamestate[$offset+$i-1] -ne 0) {
      $newGamestate = make-move $player $i $gamestate.clone()
      if ($newGamestate -eq $null) { throw "New gamestate in list-moves is null" }
      $newHeur = ( calc-heuristic $newGamestate.clone() ) * $multiplier
      $results.Add($(new-gameobject $i $newGamestate.clone() $newHeur)) | out-null
      write-debug "Added move number $($newObj.move).  Total items:  $($results.Count)"
    }
  }
  Write-Debug "Exiting list-moves"
  if ($results -eq $null) { throw "Leaving list-moves with null list" }
  $results
}

<#
function select-move {
  param ( $player, $gamestate )

  $bestMove = new-object PSObject -Property @{
    move=0;
    gamestate=@();
    heuristic=-200
  }
  $gamestateLocal = $gamestate.clone()
  $allMoves = list-moves $player $gamestateLocal
  if ($allMoves -eq $null) { throw "Received no next moves from current game state." }
  $allMoves |% {
    if ($_.heuristic -gt $bestMove.heuristic) { $bestMove = $_ } 
    elseif ($_.heuristic -eq $bestMove.heuristic) {
      if ((get-random -Maximum 100) -lt 50) { $bestMove = $_ }
#      $bestMove = $_
    }
  }
  if ($bestMove.move -eq $null) { throw "Player $player is being indecisive." }
  $bestMove
}
#>


function select-move {
  param ( $player, $gamestate, $depth )

  $heuristic = calc-heuristic $gamestate
  $bestMove = new-gameobject 0 @() -200

  #end game (terminal case)
  if (test-endgame $gamestate.clone()) {
    if ($player -eq 2) { $heuristic = $heuristic * -1 }
    $return = new-gameobject $move $gamestate.clone() $heuristic
    
  #max depth (terminal case)  
  } elseif ($depth -eq 0) {
    $allMoves = list-moves $player $gamestateLocal
    if ($allMoves -eq $null) { throw "Received no next moves from current game state." }
    $allMoves |% {
      if ($_.heuristic -gt $bestMove.heuristic) { $return = $_ } 
      elseif ($_.heuristic -eq $bestMove.heuristic) {
        if ((get-random -Maximum 100) -lt 50) { $return = $_ }
      }
    }
    if ($return.move -eq $null) { throw "Player $player is being indecisive." }

  #work the tree (recursive case)
  } else {
    
  }

  $return
}



### Main routine ###


$currentManacala = $initManacala
writehost-array $currentManacala
do {
  #$currentManacala = user-move 1 $currentManacala
  $player1move = $(select-move 1 $currentManacala).move
  write-host "Player 1's move:  $player1move"
  $currentManacala = make-move 1 $player1move $currentManacala
  writehost-array $currentManacala
  if (!(test-endgame $currentManacala)) { 
    #$currentManacala = user-move 2 $currentManacala
    $player2move = $(select-move 2 $currentManacala).move
    write-host "Player 2's move:  $player2move"
    $currentManacala = make-move 2 $player2move $currentManacala
    writehost-array $currentManacala
  }
  #read-host "Press [enter] to continue"
} until (test-endgame $currentManacala)
if ($currentManacala[6] -gt $currentManacala[13]) { write-host "Player 1 wins" } 
elseif ($currentManacala[6] -lt $currentManacala[13]) { write-host "Player 2 wins" } 
else { write-host "Tie" }



<#
writehost-array $initManacala
$allMoves = list-moves 1 $initManacala
$allMoves | ft
#>

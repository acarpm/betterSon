const fs=require("fs");
const b=require("/Users/alexandrucarp/Documents/Github Projects/betterSon/.ua/intermediate/batches.json").batches.find(x=>x.batchIndex===1);
const r=require("/Users/alexandrucarp/Documents/Github Projects/betterSon/.ua/tmp/ua-file-extract-results-1.json").results;
const F={
"config.py":["Gestion de la configuration utilisateur persistante (module actif, reglages) lue et ecrite en JSON dans le dossier de donnees.",["config","persistance","reglages","json"],"simple"],
"dialogue_identite.py":["Dialogues Tkinter modaux pour saisir le nom du poste et gerer la liste des techniciens, avec un widget SelecteurTechnicien reutilisable.",["gui","dialogue","identite","tkinter"],"moderate"],
"envoi.py":["File d'envoi asynchrone des resultats de tests vers un serveur distant avec persistance locale, reprise et rattrapage des operations en attente.",["reseau","file-attente","thread","synchronisation"],"moderate"],
"gui.py":["Fenetre principale de l'application : orchestre l'en-tete, la navigation entre pages, le choix du poste, les mises a jour et la fermeture propre.",["entry-point","gui","navigation","tkinter"],"complex"],
"identite.py":["Gere l'identite du poste et des techniciens ainsi que la file des operations en attente de transmission et les lignes de signature des fichiers.",["identite","persistance","utilitaire","technicien"],"moderate"],
"instruments/gestionnaire.py":["Gestionnaire d'instruments : liste les ports serie, detecte et memorise les appareils (charge EA, Daly) et expose leur statut.",["instruments","serie","detection","service"],"moderate"],
"modules/decharge/page_encours.py":["Page Tkinter de suivi d'un test de decharge en cours : demarrage, arret, traitement de la file de mesures et analyse finale.",["page","decharge","gui","thread"],"complex"],
"modules/equilibrage/page_session.py":["Page de session d'equilibrage Daly : surveille l'instrument, pilote l'acquisition et affiche tensions, courant et donnees en direct.",["page","equilibrage","gui","acquisition"],"complex"],
"page_modules.py":["Page de selection des modules actifs (decharge, equilibrage, resistance) enregistree dans la configuration.",["page","gui","modules","configuration"],"simple"],
"synchro.py":["Synchronisation avec le serveur distant : appelle l'API, met a jour les techniciens et lance la synchronisation en arriere-plan.",["synchronisation","reseau","thread","api-client"],"simple"],
"updater.py":["Mise a jour automatique : verifie la derniere version, telecharge, controle la somme et remplace l'application (Windows/macOS) avant relance.",["mise-a-jour","reseau","installation","multiplateforme"],"complex"],
"version.py":["Definit le numero de version de l'application.",["version","constante","configuration"],"simple"]};
const S={
"config.py":{charger:"Charge la configuration JSON depuis le disque.",sauver:"Ecrit la configuration sur le disque.",module_actif:"Indique si un module est active.",definir_module:"Active ou desactive un module et sauvegarde.",reglage:"Lit la valeur d'un reglage.",definir_reglage:"Modifie un reglage et sauvegarde."},
"dialogue_identite.py":{demander_poste:"Dialogue modal demandant le nom du poste.",gerer_techniciens:"Dialogue modal d'ajout, de suppression et de gestion des techniciens.",SelecteurTechnicien:"Widget de selection du technicien avec bouton de gestion."},
"envoi.py":{_poster:"Envoie une requete HTTP POST au serveur distant.",_noter_envoyes:"Marque les operations transmises dans la file locale.",_boucle:"Boucle du thread d'envoi qui vide la file periodiquement.",envoyer:"Ajoute une operation a la file et declenche l'envoi.",rattraper:"Renvoie les operations anterieures non transmises.",reprendre:"Relance l'envoi des operations en attente."},
"identite.py":{nettoyer:"Normalise une chaine d'identite.",poste:"Retourne le nom du poste.",definir_poste:"Enregistre le nom du poste.",techniciens:"Liste les techniciens connus.",ajouter_technicien:"Ajoute un technicien.",supprimer_technicien:"Supprime un technicien.",operations_en_attente:"Liste les operations non transmises.",operation_transmise:"Marque une operation comme transmise.",remplacer_techniciens:"Remplace la liste des techniciens par celle du serveur.",dernier_technicien:"Retourne le dernier technicien utilise.",retenir_technicien:"Memorise le technicien courant.",lignes_signature:"Construit les lignes de signature des fichiers de resultats.",lire_entete:"Lit l'en-tete d'identite d'un fichier de resultats."},
"synchro.py":{etat:"Retourne l'etat de la synchronisation.",synchroniser:"Synchronise techniciens et operations avec le serveur.",lancer:"Lance la synchronisation dans un thread."},
"updater.py":{ErreurMaj:"Exception levee lors d'un echec de mise a jour.",systeme:"Detecte le systeme d'exploitation.",installe:"Indique si l'application est installee en mode packagee.",_contexte_ssl:"Construit le contexte SSL pour les requetes.",_expliquer:"Traduit une erreur reseau en message lisible.",verifier:"Verifie la presence d'une nouvelle version.",derniere_version:"Retourne la derniere version publiee.",plus_recente:"Compare deux numeros de version.",telecharger:"Telecharge l'archive de mise a jour et verifie sa somme.",_remplacer_fichier:"Remplace l'executable courant par le nouveau.",_remplacer_app:"Remplace le bundle .app sur macOS.",_cible_macos:"Determine le dossier cible de l'app macOS.",appliquer:"Applique la mise a jour selon la plateforme.",relancer:"Relance l'application apres mise a jour.",nettoyer:"Supprime les fichiers temporaires de mise a jour."},
"gui.py":{Application:"Classe principale Tk : en-tete, pages, navigation, etat occupe, mises a jour et fermeture."},
"instruments/gestionnaire.py":{Gestionnaire:"Detecte, teste et memorise les instruments serie et expose port, origine et statut."},
"modules/decharge/page_encours.py":{PageEnCours:"Page de test de decharge : demarre/arrete le test, traite la file de mesures, affiche l'analyse."},
"modules/equilibrage/page_session.py":{PageSession:"Page de session d'equilibrage : surveillance instrument, demarrage/arret, traitement des donnees."},
"page_modules.py":{PageModules:"Page cochant les modules a activer."}};
const nodes=[],edges=[];
const E=(s,t,type,w)=>edges.push({source:s,target:t,type,direction:"forward",weight:w});
for(const x of r){
 const [sum,tags,cx]=F[x.path];
 const fid="file:"+x.path;
 nodes.push({id:fid,type:"file",name:x.path.split("/").pop(),filePath:x.path,summary:sum,tags,complexity:cx});
 const items=[];
 for(const f of x.functions||[]) if(!f.name.startsWith("_")||f.endLine-f.startLine+1>=10) items.push(["function",f]);
 for(const c of x.classes||[]) items.push(["class",c]);
 for(const [k,f] of items){
  const id=`${k}:${x.path}:${f.name}`;
  const s=(S[x.path]||{})[f.name]||f.name;
  const n=f.endLine-f.startLine+1;
  nodes.push({id,type:k,name:f.name,filePath:x.path,lineRange:[f.startLine,f.endLine],summary:s,tags:k==="class"?["classe",...tags.slice(0,2)]:["fonction",...tags.slice(0,2)],complexity:n>60?"complex":n>=20?"moderate":"simple"});
  E(fid,id,"contains",1.0);
  if((x.exports||[]).some(e=>e.name===f.name)&&!f.name.startsWith("_")) E(fid,id,"exports",0.8);
 }
 for(const p of b.batchImportData[x.path]) E(fid,"file:"+p,"imports",0.7);
}
E("file:gui.py","class:modules/equilibrage/page_session.py:PageSession","depends_on",0.6);
fs.writeFileSync("intermediate/batch-1.json",JSON.stringify({nodes,edges},null,1));
console.log(nodes.length,edges.length);

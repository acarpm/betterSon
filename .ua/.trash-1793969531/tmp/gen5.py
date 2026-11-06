import json
nodes=[];edges=[]
def f(p,s,t,c):
    nodes.append(dict(id="file:"+p,type="file",name=p.split("/")[-1],filePath=p,summary=s,tags=t,complexity=c))
def sym(kind,p,n,r,s,t,c):
    i=f"{kind}:{p}:{n}"
    nodes.append(dict(id=i,type=kind,name=n,filePath=p,lineRange=r,summary=s,tags=t,complexity=c))
    edges.append(dict(source="file:"+p,target=i,type="contains",direction="forward",weight=1.0))
    edges.append(dict(source="file:"+p,target=i,type="exports",direction="forward",weight=0.8))
C="modules/resistance/calcul.py";M="modules/resistance/mesure.py";E="modules/resistance/page_encours.py";R="modules/resistance/page_resultats.py";S="modules/resistance/resultats.py";W="modules/resistance/widgets.py"
f(C,"Calculs purs de resistance interne (en mOhm) a partir des mesures de tension et courant des essais : moyennes, resistance par essai, statistiques et synthese.",["calcul","resistance-interne","utilitaire","mesure"],"moderate")
f(M,"Thread de mesure qui pilote l'equilibreur Daly pendant un essai de resistance interne et enchaine la sequence d'acquisition.",["thread","acquisition","resistance-interne","instrument"],"moderate")
f(E,"Page Tkinter de test en cours du module resistance : demarrage/arret de la mesure, traitement de la file d'essais, envoi des resultats et affichage de l'analyse.",["ui","tkinter","page","resistance-interne"],"complex")
f(R,"Page Tkinter listant les resultats de resistance interne enregistres, avec filtrage, affichage des barres et ouverture des CSV.",["ui","tkinter","page","resultats"],"moderate")
f(S,"Lecture et analyse des fichiers CSV de resultats de resistance interne, produisant les syntheses par fichier ou par dossier.",["analyse","csv","resultats","resistance-interne"],"moderate")
f(W,"Widget graphique de barres de resistance par cellule et formatage du texte en mOhm.",["widget","ui","graphique","tkinter"],"simple")
for n,r,s in [("moyenne",[17,19],"Calcule la moyenne d'une liste de valeurs."),("_r_mohm",[22,25],"Convertit une difference tension/courant en resistance en mOhm."),("_moyenne_cellules",[28,30],"Moyenne des valeurs par cellule."),("resistance_essai",[33,47],"Calcule la resistance interne de chaque cellule pour un essai."),("resistances",[50,53],"Calcule les resistances pour l'ensemble des essais."),("_stats",[56,61],"Calcule des statistiques simples sur les resistances."),("synthese",[64,80],"Produit la synthese finale des resistances par cellule.")]:
    sym("function",C,n,r,s,["calcul","resistance-interne","utilitaire"],"simple")
sym("class",M,"Mesure",[29,129],"Thread de mesure : demarre, arrete et execute la sequence d'essais en interrogeant l'equilibreur Daly.",["thread","acquisition","instrument"],"moderate")
sym("class",E,"PageEnCours",[20,181],"Page de test en cours : gere les boutons, l'etat, la file d'essais et la fin de test avec envoi et analyse.",["ui","page","tkinter","etat"],"complex")
sym("class",R,"PageResultats",[14,127],"Page des resultats : liste filtrable, affichage detaille et ouverture des CSV.",["ui","page","tkinter","resultats"],"moderate")
for n,r,s in [("lister",[15,16],"Liste les fichiers de resultats d'un dossier."),("_nombre",[19,23],"Convertit une valeur CSV en nombre."),("analyser",[26,57],"Analyse un fichier CSV de resultats et en tire la synthese."),("analyser_dossier",[60,63],"Analyse tous les CSV d'un dossier.")]:
    sym("function",S,n,r,s,["analyse","csv","resultats"],"simple")
sym("class",W,"BarresResistance",[7,47],"Widget dessinant des barres de resistance par cellule.",["widget","graphique","tkinter"],"simple")
sym("function",W,"texte_mohm",[50,51],"Formate une valeur en texte mOhm.",["formatage","utilitaire","ui"],"simple")
imp={"modules/resistance/mesure.py":["instruments/__init__.py","instruments/daly.py","modules/resistance/calcul.py"],"modules/resistance/page_encours.py":["envoi.py","identite.py","modules/resistance/calcul.py","modules/resistance/mesure.py","modules/resistance/profils.py","modules/resistance/widgets.py","theme.py"],"modules/resistance/page_resultats.py":["modules/resistance/chemins.py","modules/resistance/page_encours.py","modules/resistance/resultats.py","modules/resistance/widgets.py","theme.py"],"modules/resistance/resultats.py":["identite.py","modules/resistance/calcul.py"],"modules/resistance/widgets.py":["theme.py"]}
for s,ts in imp.items():
    for t in ts: edges.append(dict(source="file:"+s,target="file:"+t,type="imports",direction="forward",weight=0.7))
edges.append(dict(source="class:"+M+":Mesure",target="class:instruments/daly.py:Daly",type="calls",direction="forward",weight=0.8))
json.dump(dict(nodes=nodes,edges=edges),open(".ua/intermediate/batch-5.json","w"),ensure_ascii=False,indent=1)
print(len(nodes),len(edges))

import pulp
import pandas as pd

class DietFormulator:
    def __init__(self, ingredients_df, nutrient_list, requirements, limits=None, selected_species=None, selected_stage=None, ratios=None):
        """
        ingredients_df: DataFrame con columnas de nutrientes, precio e 'Ingrediente'
        nutrient_list: lista de nombres de nutrientes a optimizar y analizar
        requirements: dict {nutriente: {"min": valor_min, "max": valor_max}}
        limits: dict {"min": {ing: vmin}, "max": {ing: vmax}} (en %)
        selected_species, selected_stage: opcionales, por compatibilidad
        ratios: lista de dicts con ratios, por ejemplo:
            [
                {
                    "numerador": "LYS_DR",
                    "denominador": "THR_DR",
                    "operador": ">=",
                    "valor": 0.8
                }
            ]
        """
        self.nutrient_list = nutrient_list
        self.requirements = requirements
        self.ingredients_df = ingredients_df
        self.selected_species = selected_species
        self.selected_stage = selected_stage
        # Asegura que limits tenga las claves necesarias
        self.limits = limits if limits else {}
        self.limits.setdefault("min", {})
        self.limits.setdefault("max", {})
        self.ratios = ratios or []

    @staticmethod
    def _normalize_bound(value):
        try:
            bound = float(value)
        except Exception:
            return 0.0
        return bound if bound > 0 else 0.0

    @staticmethod
    def _error_result(message):
        return {
            "success": False,
            "message": message,
            "diet": {},
            "cost": 0,
            "nutritional_values": {},
            "compliance_data": [],
            "shadow_prices": {}
        }

    def run(self):
        prob = pulp.LpProblem("Diet_Formulation", pulp.LpMinimize)
        ingredient_vars = pulp.LpVariable.dicts(
            "Ing", self.ingredients_df.index, lowBound=0, upBound=1, cat="Continuous"
        )
        prob += pulp.lpSum(
            [self.ingredients_df.loc[i, "precio"] * ingredient_vars[i] for i in self.ingredients_df.index]
        ), "Total_Cost"
        prob += pulp.lpSum([ingredient_vars[i] for i in self.ingredients_df.index]) == 1, "Total_Proportion"

        # Límites de inclusión por ingrediente
        for i in self.ingredients_df.index:
            ing_name = self.ingredients_df.loc[i, "Ingrediente"]
            # Manejo seguro de límites para evitar KeyError
            min_inc = self.limits.get("min", {}).get(ing_name, 0) / 100
            max_inc = self.limits.get("max", {}).get(ing_name, 100) / 100
            prob += ingredient_vars[i] >= min_inc, f"MinInc_{ing_name}"
            prob += ingredient_vars[i] <= max_inc, f"MaxInc_{ing_name}"

        # Restricciones nutricionales según requirements (solo si min o max distinto de 0)
        for nutrient in self.nutrient_list:
            req = self.requirements.get(nutrient, {})
            min_val = self._normalize_bound(req.get("min", 0))
            max_val = self._normalize_bound(req.get("max", 0))

            if min_val > 0:
                prob += pulp.lpSum(
                    [self.ingredients_df.loc[i, nutrient] * ingredient_vars[i] for i in self.ingredients_df.index]
                ) >= min_val, f"Min_{nutrient}"
            if max_val > 0:
                prob += pulp.lpSum(
                    [self.ingredients_df.loc[i, nutrient] * ingredient_vars[i] for i in self.ingredients_df.index]
                ) <= max_val, f"Max_{nutrient}"

        # === RESTRICCIONES DE RATIOS ENTRE NUTRIENTES ===
        for idx, ratio in enumerate(self.ratios):
            num = ratio.get("numerador")
            den = ratio.get("denominador")
            op = ratio.get("operador")
            try:
                val = float(ratio.get("valor"))
            except Exception:
                return self._error_result(f"Ratio inválido en posición {idx + 1}: valor no numérico.")

            if op not in {">=", "<=", "="}:
                return self._error_result(
                    f"Ratio inválido en posición {idx + 1}: operador '{op}' no soportado."
                )
            if num == den:
                return self._error_result(
                    f"Ratio inválido en posición {idx + 1}: numerador y denominador no pueden ser iguales."
                )
            if num not in self.nutrient_list or den not in self.nutrient_list:
                return self._error_result(
                    f"Ratio inválido en posición {idx + 1}: nutrientes fuera de la selección de formulación."
                )
            if num not in self.ingredients_df.columns or den not in self.ingredients_df.columns:
                return self._error_result(
                    f"Ratio inválido en posición {idx + 1}: nutrientes no disponibles en la matriz nutricional."
                )

            expr_num = pulp.lpSum([self.ingredients_df.loc[i, num] * ingredient_vars[i] for i in self.ingredients_df.index])
            expr_den = pulp.lpSum([self.ingredients_df.loc[i, den] * ingredient_vars[i] for i in self.ingredients_df.index])

            # Ratio linealizado: num - val*den {op} 0
            lhs = expr_num - val * expr_den
            op_key = {"<=": "LE", ">=": "GE", "=": "EQ"}[op]
            cname = f"Ratio_{num}_{op_key}_{den}_{idx}"
            if op == ">=":
                prob += lhs >= 0, cname
            elif op == "<=":
                prob += lhs <= 0, cname
            elif op == "=":
                prob += lhs == 0, cname

        # ============= DIAGNÓSTICO DESACTIVADO =============
        # (Bloque de prints removido para producción)
        # ===================================================

        prob.solve()
        diet = {}
        total_cost = 0
        nutritional_values = {}
        compliance_data = []
        shadow_prices = {}

        if pulp.LpStatus[prob.status] == "Optimal":
            for i in self.ingredients_df.index:
                amount = ingredient_vars[i].varValue * 100
                if amount > 0:
                    ingredient_name = self.ingredients_df.loc[i, "Ingrediente"]
                    diet[ingredient_name] = round(amount, 4)
                    total_cost += self.ingredients_df.loc[i, "precio"] * (amount / 100) * 100
            total_cost = round(total_cost, 2)

            # SIEMPRE calcular todos los nutrientes seleccionados, tengan o no restricción
            for nutrient in self.nutrient_list:
                valor_nut = 0
                if nutrient in self.ingredients_df.columns:
                    for i in self.ingredients_df.index:
                        amount = ingredient_vars[i].varValue * 100
                        nut_val = self.ingredients_df.loc[i, nutrient]
                        try:
                            nut_val = float(nut_val)
                        except Exception:
                            nut_val = 0
                        if pd.isna(nut_val):
                            nut_val = 0
                        valor_nut += nut_val * (amount / 100)
                nutritional_values[nutrient] = round(valor_nut, 4)

            # Para cada nutriente seleccionado, mostrar su análisis, aunque no tenga restricción
            for nutrient in self.nutrient_list:
                req = self.requirements.get(nutrient, {})
                req_min = self._normalize_bound(req.get("min", 0))
                req_max = self._normalize_bound(req.get("max", 0))
                obtenido = nutritional_values.get(nutrient, None)
                # Determinar estado
                if req_min or req_max:
                    if req_min and req_max:
                        estado = "Cumple" if (obtenido >= req_min) and (req_max == 0 or obtenido <= req_max) \
                            else ("Exceso" if (req_max != 0 and obtenido > req_max) else "Deficiente")
                    elif req_min:
                        estado = "Cumple" if obtenido >= req_min else "Deficiente"
                    elif req_max:
                        estado = "Cumple" if obtenido <= req_max else "Exceso"
                    else:
                        estado = "No definido"
                else:
                    estado = "Sin restricción"
                compliance_data.append({
                    "Nutriente": nutrient,
                    "Mínimo": req_min,
                    "Máximo": req_max,
                    "Obtenido": obtenido,
                    "Estado": estado
                })
            # Extraer shadow prices de restricciones de mínimo nutricional
            for constraint_name, constraint in prob.constraints.items():
                if constraint_name.startswith("Min_"):
                    nutrient = constraint_name[4:]  # remove "Min_" prefix
                    try:
                        shadow_prices[nutrient] = constraint.pi
                    except AttributeError:
                        shadow_prices[nutrient] = None

            return {
                "success": True,
                "diet": diet,
                "cost": total_cost,
                "nutritional_values": nutritional_values,
                "compliance_data": compliance_data,
                "shadow_prices": shadow_prices
            }
        else:
            return self._error_result(f"Solver status: {pulp.LpStatus[prob.status]}")

    # Alias para compatibilidad con apps que llaman .solve()
    def solve(self):
        return self.run()

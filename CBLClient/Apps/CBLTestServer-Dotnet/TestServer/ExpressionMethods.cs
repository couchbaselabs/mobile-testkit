// 
//  Author:
//   Hemant Rajput  <hemant.rajput@couchbase.com>
// 
//  Copyright (c) 2018 Couchbase, Inc All rights reserved.
// 
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
// 
//  http://www.apache.org/licenses/LICENSE-2.0
// 
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// 

using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;
using System.Reflection;

using Couchbase.Lite.Query;
using Couchbase.Lite.Util;

using JetBrains.Annotations;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class ExpressionMethods
    {
        internal static void ExpressionProperty([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            var prop = postBody["property"].ToString();
            response.WriteBody(Expression.Property(prop));
        }

        internal static void ExpressionMetaId([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            response.WriteBody(Meta.ID);
        }

        internal static void ExpressionSequence([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            response.WriteBody(Meta.Sequence);
        }

        internal static void ExpressionParameter([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            var parameter = postBody["parameter"].ToString();
            response.WriteBody(Expression.Parameter(parameter));
        }

        internal static void ExpressionNegated([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            IExpression expression = Expression.Value(postBody["expression"].ToString());
            response.WriteBody(Expression.Negated(expression));
        }

        internal static void ExpressionNot([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            IExpression expression = Expression.Value(postBody["expression"].ToString());
            response.WriteBody(Expression.Not(expression));
        }

        internal static void ExpressionVariable([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            var name = postBody["name"].ToString();
            response.WriteBody(ArrayExpression.Variable(name));
        }

        internal static void ExpressionAny([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<IVariableExpression>(postBody, "variable", variable => response.WriteBody(ArrayExpression.Any(variable)));
        }

        internal static void ExpressionAnyAndEvery([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<IVariableExpression>(postBody, "variable", variable => response.WriteBody(ArrayExpression.AnyAndEvery(variable)));
        }
        internal static void ExpressionEvery([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<IVariableExpression>(postBody, "variable", variable => response.WriteBody(ArrayExpression.Every(variable)));
        }
        internal static void ExpressionCreateEqualTo([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            IExpression expression1 = Expression.Value(postBody["expression1"].ToString());
            IExpression expression2 = Expression.Value(postBody["expression2"].ToString());
            response.WriteBody(expression1.EqualTo(expression2));
        }

        internal static void ExpressionCreateAnd([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            IExpression expression1 = Expression.Value(postBody["expression1"].ToString());
            IExpression expression2 = Expression.Value(postBody["expression2"].ToString());
            response.WriteBody(expression1.And(expression2));
        }

        internal static void ExpressionCreateOr([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            IExpression expression1 = Expression.Value(postBody["expression1"].ToString());
            IExpression expression2 = Expression.Value(postBody["expression2"].ToString());
            response.WriteBody(expression1.Or(expression2));
        }

        
    }
}
